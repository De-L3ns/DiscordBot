#!/usr/bin/env bash

set -Eeuo pipefail

readonly application_directory="${KLETSERBOT_APPLICATION_DIRECTORY:-/opt/kletserbot}"
readonly deployment_environment_file="${application_directory}/.deployment.env"
readonly active_compose_file="${application_directory}/compose.yaml"
readonly export_directory="${application_directory}/exports"
readonly production_volume_name="kletserbot-production-cardpack-data"
readonly service_name="kletserbot"
readonly maximum_health_wait_seconds=90

if [[ $# -ne 2 || "${2}" != "--confirm-restore" ]]; then
    echo "usage: restore-cardpack-data.sh ARCHIVE_PATH --confirm-restore" >&2
    exit 64
fi

readonly archive_path="$1"
readonly checksum_path="${archive_path}.sha256"

read_deployment_value() {
    local variable_name="$1"

    awk -F= -v requested_name="${variable_name}" \
        '$1 == requested_name { print substr($0, length($1) + 2); exit }' \
        "${deployment_environment_file}"
}

compose_command() {
    docker compose --env-file "${deployment_environment_file}" -f "${active_compose_file}" "$@"
}

restart_service() {
    compose_command up --detach --no-build "${service_name}" >/dev/null
}

archive_volume() {
    local destination_archive_path="$1"

    docker run --rm \
        --network none \
        --entrypoint tar \
        --volume "${production_volume_name}:/data:ro" \
        --volume "$(dirname "${destination_archive_path}"):/backup" \
        "${application_image}" \
        --create --gzip --file "/backup/$(basename "${destination_archive_path}")" \
        --directory /data .
}

clear_volume() {
    docker run --rm \
        --network none \
        --entrypoint sh \
        --volume "${production_volume_name}:/data" \
        "${application_image}" \
        -c 'rm -rf /data/* /data/.[!.]* /data/..?*'
}

extract_archive() {
    local source_archive_path="$1"

    docker run --rm \
        --network none \
        --entrypoint tar \
        --volume "${production_volume_name}:/data" \
        --volume "$(dirname "${source_archive_path}"):/backup:ro" \
        "${application_image}" \
        --extract --gzip --file "/backup/$(basename "${source_archive_path}")" \
        --directory /data
}

wait_for_healthy_service() {
    local container_id
    local deadline_epoch_seconds
    local health_status

    container_id="$(compose_command ps --quiet "${service_name}")"
    if [[ -z "${container_id}" ]]; then
        return 1
    fi

    deadline_epoch_seconds="$(( $(date +%s) + maximum_health_wait_seconds ))"
    while (( $(date +%s) < deadline_epoch_seconds )); do
        health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "${container_id}")"
        if [[ "${health_status}" == "healthy" ]]; then
            return 0
        fi
        if [[ "${health_status}" == "unhealthy" ]]; then
            return 1
        fi
        sleep 2
    done
    return 1
}

assert_safe_archive_entries() {
    local archive_entry

    while IFS= read -r archive_entry; do
        case "${archive_entry}" in
            /* | ../* | */../* | ..)
                echo "archive contains an unsafe path" >&2
                exit 68
                ;;
        esac
    done < <(tar --list --gzip --file "${archive_path}")
}

recover_after_failed_restore() {
    local original_exit_status="$?"
    local was_recovery_successful=true

    trap - EXIT
    set +e
    echo "restore failed; recovering the original card-pack data" >&2
    compose_command stop "${service_name}" >/dev/null 2>&1
    if [[ "${has_volume_been_modified}" == "true" ]]; then
        if ! clear_volume || ! extract_archive "${safety_archive_path}"; then
            was_recovery_successful=false
        fi
    fi

    if [[ "${was_recovery_successful}" == "true" ]]; then
        if restart_service && wait_for_healthy_service; then
            echo "original card-pack data recovered successfully" >&2
        else
            echo "data was recovered but the bot did not become healthy" >&2
        fi
    else
        echo "automatic recovery failed; the bot has been left stopped" >&2
    fi
    exit "${original_exit_status}"
}

cd "${application_directory}"
if [[ ! -f "${archive_path}" || ! -f "${checksum_path}" ]]; then
    echo "archive and matching checksum file are required" >&2
    exit 65
fi
if [[ "$(read_deployment_value "CARDPACK_DATA_VOLUME")" != "${production_volume_name}" ]]; then
    echo "refusing to restore an unexpected card-pack volume" >&2
    exit 66
fi
if ! docker volume inspect "${production_volume_name}" >/dev/null; then
    echo "production card-pack volume does not exist" >&2
    exit 67
fi

application_image="$(read_deployment_value "KLETSERBOT_IMAGE")"
readonly application_image
if [[ ! "${application_image}" =~ ^ghcr\.io/[a-z0-9._-]+/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$ ]]; then
    echo "KLETSERBOT_IMAGE must be a digest-pinned GHCR image" >&2
    exit 69
fi

sha256sum --check "${checksum_path}"
assert_safe_archive_entries

mkdir --parents "${export_directory}"
chmod 700 "${export_directory}"
safety_archive_timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
readonly safety_archive_timestamp
safety_archive_path="${export_directory}/pre-restore-cardpack-data-${safety_archive_timestamp}.tar.gz"
readonly safety_archive_path
has_volume_been_modified=false

compose_command stop "${service_name}"
trap recover_after_failed_restore EXIT
archive_volume "${safety_archive_path}"
sha256sum "${safety_archive_path}" >"${safety_archive_path}.sha256"
has_volume_been_modified=true
clear_volume
extract_archive "${archive_path}"
restart_service
wait_for_healthy_service
trap - EXIT

echo "card-pack data restored successfully"
echo "pre-restore safety export retained at: ${safety_archive_path}"
