#!/usr/bin/env bash

set -Eeuo pipefail

readonly application_directory="${KLETSERBOT_APPLICATION_DIRECTORY:-/opt/kletserbot}"
readonly deployment_environment_file="${application_directory}/.deployment.env"
readonly active_compose_file="${application_directory}/compose.yaml"
readonly export_directory="${application_directory}/exports"
readonly production_volume_name="kletserbot-production-cardpack-data"
readonly service_name="kletserbot"
readonly maximum_health_wait_seconds=90

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

cd "${application_directory}"
if [[ ! -f "${deployment_environment_file}" ]]; then
    echo "deployment environment file is missing" >&2
    exit 65
fi
if [[ "$(read_deployment_value "CARDPACK_DATA_VOLUME")" != "${production_volume_name}" ]]; then
    echo "refusing to export an unexpected card-pack volume" >&2
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
    exit 68
fi

mkdir --parents "${export_directory}"
chmod 700 "${export_directory}"
archive_timestamp="$(date --utc +%Y%m%dT%H%M%SZ)"
readonly archive_timestamp
readonly archive_path="${export_directory}/cardpack-data-${archive_timestamp}.tar.gz"

compose_command stop "${service_name}"
trap restart_service EXIT
docker run --rm \
    --network none \
    --entrypoint tar \
    --volume "${production_volume_name}:/data:ro" \
    --volume "${export_directory}:/backup" \
    "${application_image}" \
    --create --gzip --file "/backup/$(basename "${archive_path}")" --directory /data .
sha256sum "${archive_path}" >"${archive_path}.sha256"
restart_service
trap - EXIT
wait_for_healthy_service

echo "export created: ${archive_path}"
echo "checksum created: ${archive_path}.sha256"
