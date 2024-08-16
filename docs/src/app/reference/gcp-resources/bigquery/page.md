## BigQueryDataset

A dataset in Google BigQuery.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/bigquery/docs/).

### Example Usage

```python
from google.cloud import bigquery
import launchflow as lf

# Automatically creates / connects to a BigQuery Dataset in your GCP project
dataset = lf.gcp.BigQueryDataset("my_dataset")

schema = [
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("age", "INTEGER", mode="REQUIRED"),
]
table = dataset.create_table("table_name", schema=schema)

dataset.insert_table_data("table_name", [{"name": "Alice", "age": 30}])

# You can also use the underlying resource directly
# For example, for a table with columns name,age
query = f"""
SELECT name, age
FROM `{dataset.dataset_id}.table_name`
WHERE age > 10
ORDER BY age DESC
"""

for row in dataset.client().query(query):
    print(row)
```

### initialization

Create a new BigQuery Dataset resource.

**Args:**
- `name (str)`: The name of the dataset. This must be globally unique.
- `location (str)`: The location of the dataset. Defaults to "US".
- `allow_nonempty_delete (bool)`: If True, the dataset can be deleted even if it is not empty. Defaults to False.

### inputs

```python
BigQueryDataset.inputs(environment_state: EnvironmentState) -> BigQueryDatasetInputs
```

Get the inputs for the BigQuery Dataset resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment state to get the inputs for.

**Returns:**
- BigQueryDatasetInputs: The inputs for the BigQuery Dataset resource.

### dataset\_id

```python
@property
BigQueryDataset.dataset_id() -> str
```

Get the dataset id.

**Returns:**
- The dataset id.

### get\_table\_uuid

```python
BigQueryDataset.get_table_uuid(table_name: str) -> str
```

Get the table UUID, {project_id}.{dataset_id}.{table_id}.

**Args:**
- `table_name (str)`: The name of the table.

**Returns:**
- The table UUID.

### client

```python
BigQueryDataset.client() -> "bigquery.Client"
```

Get the BigQuery Client object.

**Returns:**
- The [BigQuery Client](https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client) object.

### dataset

```python
BigQueryDataset.dataset() -> "bigquery.Dataset"
```

Get the BigQuery Dataset object.

**Returns:**
- The [BigQuery Dataset](https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.dataset.Dataset) object.

### create\_table

```python
BigQueryDataset.create_table(table_name: str, *, schema: "Optional[List[bigquery.SchemaField]]" = None) -> "bigquery.Table"
```

Create a table in the dataset.

**Args:**
- `table_name (str)`: The name of the table.
- `schema (Optional[List[bigquery.SchemaField]])`: The schema of the table. Not required and defaults to None.

**Returns:**
- The [BigQuery Table](https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.table.Table) object.

**Example usage:**
```python
from google.cloud import bigquery
import launchflow as lf

dataset = lf.gcp.BigQueryDataset("my_dataset")

schema = [
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("age", "INTEGER", mode="REQUIRED"),
]
table = dataset.create_table("table_name", schema=schema)
```

### delete\_table

```python
BigQueryDataset.delete_table(table_name: str) -> None
```

Delete a table from the dataset.

**Args:**
- `table_name (str)`: The name of the table to delete.

### load\_table\_data\_from\_csv

```python
BigQueryDataset.load_table_data_from_csv(table_name: str, file_path: Path) -> None
```

Load data from a CSV file into a table.

**Args:**
- `table_name (str)`: The name of the table to load the data into.
- `file_path (Path)`: The path to the CSV file to load.

### insert\_table\_data

```python
BigQueryDataset.insert_table_data(table_name: str, rows_to_insert: List[Dict[Any, Any]]) -> None
```

Insert in-memory data into a table.
There's seems to be a bug in bigquery where if a table name is re-used (created and then deleted
recently), streaming to it won't work. If you encounter an unexpected 404 error, try changing
the table name.

**Args:**
- `table_name (str)`: The name of the table to insert the data into.
- `rows_to_insert (List[Dict[Any, Any]])`: The data to insert into the table.

**Raises:** ValueError if there were errors when inserting the data.
