import launchflow as lf

bucket = lf.gcp.GCSBucket(f"{lf.project}-{lf.environment}-bucket")
instance = lf.gcp.CloudSQLPostgres("launchflow-sample-db")
user = lf.gcp.CloudSQLUser("pg-user", instance)
db2 = lf.gcp.CloudSQLDatabase("launchflow-sample-db2", instance)
secret = lf.gcp.SecretManagerSecret("gcp-secret")
redis = lf.gcp.MemorystoreRedis("my-redis-cluster")
gce_pg = lf.gcp.ComputeEnginePostgres("pg-instance")
gce_redis = lf.gcp.ComputeEngineRedis("redis-instance")
pubsub_topic = lf.gcp.PubsubTopic("my-topic")
pubsub_sub = lf.gcp.PubsubSubscription("my-sub", pubsub_topic)
cloud_tasks = lf.gcp.CloudTasksQueue("my-queue")
