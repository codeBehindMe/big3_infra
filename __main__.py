"""A Google Cloud Python Pulumi program"""

from typing import Final

import pulumi
import pulumi_gcp as gcp

gcp_conf = pulumi.Config("gcp")

REGION: Final[str] = "australia-southeast1"
PROJECT: Final[str] = gcp_conf.require("project")
# BEGIN
# Some common infrastructure
artifact_registry_api_enable = gcp.projects.Service(
    resource_name="artifiact_registry_api_enable",
    disable_dependent_services=True,
    disable_on_destroy=True,
    service="artifactregistry.googleapis.com",
    project=PROJECT,
)
artifact_registry = gcp.artifactregistry.Repository(
    resource_name="docker_repo",
    format="DOCKER",
    location=REGION,
    repository_id="big3-docker",
    project=PROJECT,
    opts=pulumi.ResourceOptions(depends_on=artifact_registry_api_enable),
)
# END

# BEGIN
# Big3 Web Application Infrstructure
build_agent_sa = gcp.serviceaccount.Account(
    resource_name="build_agent_sa",
    account_id="bigbuilder",
    display_name="Big3 Svelte App deployment GitHub Actions service account",
    project=PROJECT,
)

pulumi.export("build_sa_email", build_agent_sa.email)

# Runtime service account
runtime_sa = gcp.serviceaccount.Account(
    resource_name="runtime_sa",
    account_id="bigrunner",
    display_name="Big3 App Cloud Run Service Account",
    project=PROJECT,
)

# Give the builld service account the ability to act as th run service account
buld_sa_act_as_run_sa_binding = gcp.serviceaccount.IAMBinding(
    resource_name="buld_sa_act_as_run_sa_binding",
    service_account_id=runtime_sa.name,
    role="roles/iam.serviceAccountUser",
    members=[build_agent_sa.email.apply(lambda e: f"serviceAccount:{e}")],
)

pulumi.export("run_sa_email", runtime_sa.email)

cloud_run_developer_member = gcp.projects.IAMMember(
    resource_name="cloud_run_developer",
    role="roles/run.developer",
    member=build_agent_sa.email.apply(lambda e: f"serviceAccount:{e}"),
    project=PROJECT,
)

artifact_registry_repoadmin_member = gcp.projects.IAMMember(
    resource_name="artifact_registry_repoadmin_member",
    role="roles/artifactregistry.repoAdmin",
    member=build_agent_sa.email.apply(lambda e: f"serviceAccount:{e}"),
    project=PROJECT,
)


# WIF
iam_creds_api = gcp.projects.Service(
    resource_name="iam_creds_api",
    disable_dependent_services=True,
    disable_on_destroy=True,
    service="iamcredentials.googleapis.com",
    project=PROJECT,
)


run_admin_api = gcp.projects.Service(
    resource_name="run_admin_api",
    disable_dependent_services=True,
    disable_on_destroy=True,
    service="run.googleapis.com",
    project=PROJECT,
)

wif_pool = gcp.iam.WorkloadIdentityPool(
    resource_name="wif_pool",
    description="WIF Pool for GitHub Actions",
    display_name="GitHub Actions Identity Pool",
    workload_identity_pool_id="github-wif-pool-1",
    project=PROJECT,
)

wif_provider = gcp.iam.WorkloadIdentityPoolProvider(
    resource_name="wif_provider",
    workload_identity_pool_id=wif_pool.workload_identity_pool_id,
    workload_identity_pool_provider_id="big3-github-actions-provider",
    display_name="Big3 Web Frontend GA",
    description="Github Actions provider for CI/CD for Big3 web frontend",
    attribute_mapping={"google.subject": "assertion.sub"},
    attribute_condition=f"assertion.repository=='codeBehindMe/big3'",
    oidc=gcp.iam.WorkloadIdentityPoolProviderOidcArgs(
        issuer_uri="https://token.actions.githubusercontent.com"
    ),
    project=PROJECT,
)

pulumi.export("wif_provider_name", wif_provider.name)

wif_builder_bind = gcp.serviceaccount.IAMBinding(
    resource_name="wif_builder_binding",
    service_account_id=build_agent_sa.name,
    role="roles/iam.workloadIdentityUser",
    members=[wif_pool.name.apply(lambda x: f"principalSet://iam.googleapis.com/{x}/*")],
)

# END

# BEGIN
# firestore database
firestore_db = gcp.firestore.Database(
    resource_name="firestore_database",
    app_engine_integration_mode="DISABLED",
    concurrency_mode="OPTIMISTIC",
    delete_protection_state="DELETE_PROTECTION_DISABLED",
    name="devfsdb",
    location_id="australia-southeast2",
    point_in_time_recovery_enablement="POINT_IN_TIME_RECOVERY_DISABLED",
    project=PROJECT,
    type="FIRESTORE_NATIVE",
)
# END
