#!/usr/bin/env bash

set -Eeuo pipefail

readonly application_directory="${KLETSERBOT_APPLICATION_DIRECTORY:-/opt/kletserbot}"
readonly active_compose_file="${application_directory}/compose.yaml"
readonly previous_compose_file="${application_directory}/compose.previous.yaml"
readonly deployment_environment_file="${application_directory}/.deployment.env"
readonly previous_deployment_environment_file="${application_directory}/.deployment.previous.env"
readonly service_name="kletserbot"
readonly maximum_health_wait_seconds=90

if [[ ! -f "${previous_compose_file}" || ! -f "${previous_deployment_environment_file}" ]]; then
    echo "no previous deployment is available" >&2
    exit 65
fi

compose_command() {
    docker compose --env-file "${deployment_environment_file}" -f "${active_compose_file}" "$@"
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
rollback_compose_file="$(mktemp "${application_directory}/compose.rollback.XXXXXX.yaml")"
rollback_environment_file="$(mktemp "${application_directory}/.deployment.rollback.XXXXXX.env")"
readonly rollback_compose_file
readonly rollback_environment_file
trap 'rm -f "${rollback_compose_file}" "${rollback_environment_file}"' EXIT

cp "${active_compose_file}" "${rollback_compose_file}"
cp "${deployment_environment_file}" "${rollback_environment_file}"
cp "${previous_compose_file}" "${active_compose_file}"
cp "${previous_deployment_environment_file}" "${deployment_environment_file}"

if compose_command up --detach --no-build --remove-orphans && wait_for_healthy_service; then
    cp "${rollback_compose_file}" "${previous_compose_file}"
    cp "${rollback_environment_file}" "${previous_deployment_environment_file}"
    echo "rollback completed successfully"
    exit 0
fi

echo "rollback failed; restoring the release that was active before rollback" >&2
cp "${rollback_compose_file}" "${active_compose_file}"
cp "${rollback_environment_file}" "${deployment_environment_file}"
compose_command up --detach --no-build --remove-orphans
exit 1
