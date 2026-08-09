#!/usr/bin/env bash

set -Eeuo pipefail

readonly application_directory="${KLETSERBOT_APPLICATION_DIRECTORY:-/opt/kletserbot}"
readonly active_compose_file="${application_directory}/compose.yaml"
readonly candidate_compose_file="${application_directory}/compose.yaml.candidate"
readonly previous_compose_file="${application_directory}/compose.previous.yaml"
readonly deployment_environment_file="${application_directory}/.deployment.env"
readonly previous_deployment_environment_file="${application_directory}/.deployment.previous.env"
readonly production_environment_file="${application_directory}/.env.production"
readonly service_name="kletserbot"
readonly maximum_health_wait_seconds=90

if [[ $# -ne 1 ]]; then
    echo "usage: deploy-production.sh IMAGE_REFERENCE" >&2
    exit 64
fi

readonly image_reference="$1"

read_deployment_value() {
    local variable_name="$1"
    local deployment_value

    deployment_value="$(
        awk -F= -v requested_name="${variable_name}" \
            '$1 == requested_name { print substr($0, length($1) + 2); exit }' \
            "${deployment_environment_file}"
    )"
    if [[ -z "${deployment_value}" ]]; then
        echo "${variable_name} is missing from ${deployment_environment_file}" >&2
        exit 65
    fi

    printf '%s' "${deployment_value}"
}

assert_regular_file() {
    local file_path="$1"

    if [[ ! -f "${file_path}" ]]; then
        echo "required file is missing: ${file_path}" >&2
        exit 66
    fi
}

assert_production_environment_permissions() {
    local permission_mode
    local owner_name

    assert_regular_file "${production_environment_file}"
    permission_mode="$(stat --format='%a' "${production_environment_file}")"
    owner_name="$(stat --format='%U' "${production_environment_file}")"
    if [[ "${owner_name}" != "deploy" || "${permission_mode}" != "600" ]]; then
        echo "${production_environment_file} must be owned by deploy with mode 600" >&2
        exit 67
    fi
}

assert_image_reference() {
    local expected_image_repository

    expected_image_repository="$(read_deployment_value "KLETSERBOT_IMAGE_REPOSITORY")"
    if [[ ! "${expected_image_repository}" =~ ^ghcr\.io/[a-z0-9._-]+/[a-z0-9._/-]+$ ]]; then
        echo "KLETSERBOT_IMAGE_REPOSITORY is invalid" >&2
        exit 68
    fi
    if [[ ! "${image_reference}" =~ ^ghcr\.io/[a-z0-9._-]+/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$ ]]; then
        echo "image reference must be a lower-case GHCR digest reference" >&2
        exit 69
    fi
    if [[ "${image_reference}" != "${expected_image_repository}"@* ]]; then
        echo "image reference is not for the configured GHCR repository" >&2
        exit 70
    fi
}

write_candidate_deployment_environment() {
    local candidate_environment_file="$1"
    local cardpack_data_volume
    local expected_image_repository

    cardpack_data_volume="$(read_deployment_value "CARDPACK_DATA_VOLUME")"
    expected_image_repository="$(read_deployment_value "KLETSERBOT_IMAGE_REPOSITORY")"
    if [[ "${cardpack_data_volume}" != "kletserbot-production-cardpack-data" ]]; then
        echo "CARDPACK_DATA_VOLUME must name the production card-pack volume" >&2
        exit 71
    fi

    umask 077
    {
        printf 'KLETSERBOT_ENV_FILE=.env.production\n'
        printf 'KLETSERBOT_IMAGE_REPOSITORY=%s\n' "${expected_image_repository}"
        printf 'KLETSERBOT_IMAGE=%s\n' "${image_reference}"
        printf 'CARDPACK_DATA_VOLUME=%s\n' "${cardpack_data_volume}"
    } >"${candidate_environment_file}"
}

compose_command() {
    docker compose --env-file "${deployment_environment_file}" -f "${active_compose_file}" "$@"
}

wait_for_healthy_service() {
    local container_id
    local initial_restart_count
    local health_status
    local restart_count
    local deadline_epoch_seconds

    container_id="$(compose_command ps --quiet "${service_name}")"
    if [[ -z "${container_id}" ]]; then
        echo "${service_name} container was not created" >&2
        return 1
    fi

    initial_restart_count="$(docker inspect --format '{{.RestartCount}}' "${container_id}")"
    deadline_epoch_seconds="$(( $(date +%s) + maximum_health_wait_seconds ))"
    while (( $(date +%s) < deadline_epoch_seconds )); do
        health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "${container_id}")"
        restart_count="$(docker inspect --format '{{.RestartCount}}' "${container_id}")"
        if [[ "${health_status}" == "healthy" && "${restart_count}" == "${initial_restart_count}" ]]; then
            return 0
        fi
        if [[ "${health_status}" == "unhealthy" || "${restart_count}" != "${initial_restart_count}" ]]; then
            echo "${service_name} failed health verification" >&2
            return 1
        fi
        sleep 2
    done

    echo "${service_name} did not become healthy within ${maximum_health_wait_seconds} seconds" >&2
    return 1
}

restore_previous_release() {
    if [[ ! -f "${previous_compose_file}" || ! -f "${previous_deployment_environment_file}" ]]; then
        echo "no previous release is available for rollback" >&2
        return 1
    fi

    cp "${previous_compose_file}" "${active_compose_file}"
    cp "${previous_deployment_environment_file}" "${deployment_environment_file}"
    compose_command up --detach --no-build --remove-orphans
    wait_for_healthy_service
}

main() {
    local candidate_environment_file

    cd "${application_directory}"
    assert_regular_file "${deployment_environment_file}"
    assert_regular_file "${candidate_compose_file}"
    assert_production_environment_permissions
    assert_image_reference

    candidate_environment_file="$(mktemp "${application_directory}/.deployment.candidate.XXXXXX")"
    trap 'rm -f "${candidate_environment_file}"' EXIT
    write_candidate_deployment_environment "${candidate_environment_file}"

    docker compose --env-file "${candidate_environment_file}" -f "${candidate_compose_file}" config --quiet
    docker pull "${image_reference}"

    cp "${active_compose_file}" "${previous_compose_file}"
    cp "${deployment_environment_file}" "${previous_deployment_environment_file}"
    mv "${candidate_compose_file}" "${active_compose_file}"
    mv "${candidate_environment_file}" "${deployment_environment_file}"
    trap - EXIT

    if compose_command up --detach --no-build --remove-orphans && wait_for_healthy_service; then
        echo "deployment completed successfully"
        return 0
    fi

    echo "deployment failed; attempting rollback" >&2
    if restore_previous_release; then
        echo "rollback completed successfully" >&2
    else
        echo "deployment and rollback both failed; inspect container logs immediately" >&2
    fi
    return 1
}

main
