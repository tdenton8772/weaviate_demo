import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
import weaviate.classes.config as wvcc
from weaviate.classes.config import ReferenceProperty
import json
from weaviate.classes.query import Filter
from weaviate.classes.query import QueryReference

client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    additional_config=AdditionalConfig(
        timeout=Timeout(init=30, query=60, insert=120)
    )
)

try:
    category_collection = client.collections.get("Product")
    x = 0
    for item in category_collection.iterator(include_vector=True, 
                                            return_references=QueryReference(
                                                                link_on="category_reference",
                                                                return_properties=["name"]
                                                            )
                                            ):
        print(item.uuid, item.properties.get("name_title"))
        print(item.uuid, item.references)
        if x==10:
            exit(1)
        x+=1
finally:
    client.close()