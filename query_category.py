import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
import weaviate.classes.config as wvcc
from weaviate.classes.config import ReferenceProperty
import json
from weaviate.classes.query import Filter

client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    additional_config=AdditionalConfig(
        timeout=Timeout(init=30, query=60, insert=120)
    )
)

try:
    category_collection = client.collections.get("Category")

    for item in category_collection.iterator():
        print(item.uuid, item.properties)

finally:
    client.close()