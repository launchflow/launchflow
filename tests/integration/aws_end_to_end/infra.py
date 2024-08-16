import launchflow as lf

bucket = lf.aws.S3Bucket(f"{lf.project}-{lf.environment}-bucket")
db = lf.aws.RDSPostgres("launchflow-sample-db")
secret = lf.aws.SecretsManagerSecret("aws-secret", recovery_window_in_days=0)
# redis = lf.aws.ElasticacheRedis("my-redis-cluster")
ec2_pg = lf.aws.EC2Postgres("pg-instance")
ec2_redis = lf.aws.EC2Redis("redis-instance")
