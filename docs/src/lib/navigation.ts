export const homeNavigation = [
  {
    title: 'Introduction',
    links: [
      { title: 'Welcome', href: '/' },
      { title: 'Get Started', href: '/docs/get-started' },
      { title: 'Why LaunchFlow', href: '/docs/why-launchflow' },
    ],
  },
  {
    title: 'Concepts',
    links: [
      { title: 'Resources', href: '/docs/concepts/resources' },
      { title: 'Services', href: '/docs/concepts/services' },
      { title: 'Environments', href: '/docs/concepts/environments' },
    ],
  },
  {
    title: 'User Guides',
    links: [
      { title: 'Secrets', href: '/docs/user-guides/secrets' },
      {
        title: 'Dynamic Resource Names',
        href: '/docs/user-guides/access-proj-env',
      },
      {
        title: 'Use LaunchFlow with an Existing Application',
        href: '/docs/user-guides/add-to-existing',
      },
    ],
  },
  {
    title: 'Framework Guides',
    links: [
      { title: 'FastAPI Integration', href: '/docs/framework-guides/fastapi' },
      { title: 'Flask Integration', href: '/docs/framework-guides/flask' },
      { title: 'Django Integration', href: '/docs/framework-guides/django' },
    ],
  },
  {
    title: 'LaunchFlow Cloud',
    links: [
      { title: 'Overview', href: '/docs/launchflow-cloud/overview' },
      {
        title: 'GitHub Integration',
        href: '/docs/launchflow-cloud/github-deployments',
      },
    ],
  },
]

// TODO Consider generating this from dynamically from the generated reference pages,
// showing nice titles without hardcoding a map might be tricky
export const referenceNavigation = [
  {
    title: 'Reference',
    links: [{ title: 'Overview', href: '/reference' }],
  },
  {
    title: 'CLI',
    links: [{ title: 'Commands', href: '/reference/cli' }],
  },
  {
    title: 'Services',
    links: [
      { title: 'AWS ECS Fargate', href: '/reference/aws-services/ecs-fargate' },
      { title: 'GCP Cloud Run', href: '/reference/gcp-services/cloud-run' },
      {
        title: 'GCP Compute Engine',
        href: '/reference/gcp-services/compute-engine-service',
      },
      {
        title: 'GKE Kubernetes Service',
        href: '/reference/gcp-services/gke-service',
      },
    ],
  },
  {
    title: 'GCP Resources',
    links: [
      { title: 'GCS Bucket', href: '/reference/gcp-resources/gcs' },
      { title: 'Cloud SQL', href: '/reference/gcp-resources/cloudsql' },
      {
        title: 'Compute Engine',
        href: '/reference/gcp-resources/compute-engine',
      },
      { title: 'Pub/Sub', href: '/reference/gcp-resources/pubsub' },
      { title: 'Cloud Tasks', href: '/reference/gcp-resources/cloud-tasks' },
      { title: 'Memorystore', href: '/reference/gcp-resources/memorystore' },
      {
        title: 'Secret Manager',
        href: '/reference/gcp-resources/secret-manager',
      },
      { title: 'BigQuery', href: '/reference/gcp-resources/bigquery' },
      {
        title: 'Artifact Registry Repository',
        href: '/reference/gcp-resources/artifact-registry-repository',
      },
      {
        title: 'Cloud Run Container',
        href: '/reference/gcp-resources/cloud-run-container',
      },
      {
        title: 'Custom Domain Mapping',
        href: '/reference/gcp-resources/custom-domain-mapping',
      },
      {
        title: 'Regional Autoscaler',
        href: '/reference/gcp-resources/regional-autoscaler',
      },
      {
        title: 'Regional Managed Instance Group',
        href: '/reference/gcp-resources/regional-managed-instance-group',
      },
      {
        title: 'Firewall Rule',
        href: '/reference/gcp-resources/networking',
      },
      {
        title: 'HTTP Health Check',
        href: '/reference/gcp-resources/http-health-check',
      },
      {
        title: 'SSL Certificates',
        href: '/reference/gcp-resources/ssl',
      },
      {
        title: 'Global IP Address',
        href: '/reference/gcp-resources/global-ip-address',
      },
      {
        title: 'Google Kubernetes Engine',
        href: '/reference/gcp-resources/gke',
      },
      {
        title: 'GKE Custom Domain Mapping',
        href: '/reference/gcp-resources/gke-custom-domain-mapping',
      },
    ].sort((a, b) => a.title.localeCompare(b.title)),
  },
  {
    title: 'AWS Resources',
    links: [
      { title: 'S3 Bucket', href: '/reference/aws-resources/s3' },
      { title: 'RDS', href: '/reference/aws-resources/rds' },
      {
        title: 'Elasticache',
        href: '/reference/aws-resources/elasticache',
      },
      {
        title: 'EC2',
        href: '/reference/aws-resources/ec2',
      },
      {
        title: 'Secrets Manager',
        href: '/reference/aws-resources/secrets-manager',
      },
      {
        title: 'CodeBuild Project',
        href: '/reference/aws-resources/codebuild-project',
      },
      {
        title: 'ECR Repository',
        href: '/reference/aws-resources/ecr-repository',
      },
      { title: 'ECS Cluster', href: '/reference/aws-resources/ecs-cluster' },
      {
        title: 'ECS Fargate Service Container',
        href: '/reference/aws-resources/ecs-fargate-container',
      },
      {
        title: 'SQS Queue',
        href: '/reference/aws-resources/sqs',
      },
    ].sort((a, b) => a.title.localeCompare(b.title)),
  },
  {
    title: 'Kubernetes Resources',
    links: [
      { title: 'Service', href: '/reference/kubernetes-resources/service' },
      {
        title: 'Horizonal Pod Autoscaler',
        href: '/reference/kubernetes-resources/hpa',
      },
    ],
  },
  {
    title: 'Schemas',
    links: [{ title: 'LaunchFlow Yaml', href: '/reference/launchflow-yaml' }],
  },
  {
    title: 'Utilities',
    links: [
      { title: 'launchflow.fastapi', href: '/reference/python-client/fastapi' },
    ],
  },
]
