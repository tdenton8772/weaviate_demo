# cli_example.py

import argparse
import os
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.collections.classes.filters import Filter
from weaviate.classes.query import QueryReference

load_dotenv()

def connect_client():
    return weaviate.connect_to_local(
        port=8080,
        grpc_port=50051,
        additional_config=AdditionalConfig(
            timeout=Timeout(init=30, query=60, insert=60)
        )
    )

def semantic_search(query: str, top_k: int = 5, index_name: str="combined"):
    client = connect_client()
    try:
        collection = client.collections.get("Product")
        results = collection.query.near_text(query=query, target_vector=index_name, limit=top_k)
        print(f"\nTop {top_k} results for: '{query}'\n")
        for idx, obj in enumerate(results.objects, 1):
            props = obj.properties
            print(f"{idx}. {props.get('name_title')} - ${props.get('category')}")
    finally:
        client.close()

def list_by_category(user_query: str, top_k: int = 20):
    client = connect_client()
    try:
        # 1. Semantic search over Category
        category_collection = client.collections.get("Category")
        category_results = category_collection.query.near_text(user_query, limit=1)

        if not category_results.objects:
            print(f"No category matched query: {user_query}")
            return

        best_category = category_results.objects[0]
        category_uuid = best_category.uuid
        category_name = best_category.properties.get("name", "Unknown")

        # 2. Filter Product collection by category_reference.uuid
        product_collection = client.collections.get("Product")

        results = product_collection.query.fetch_objects(
            filters=Filter.by_ref("category_reference").by_id().equal(category_uuid),
            limit=top_k,
            return_references=QueryReference(
                link_on="category_reference",
                return_properties=["name"]
            )
        )

        print(f"\nProducts in category: '{category_name}'\n")
        if not results.objects:
            print("No products found in this category.")
            return

        for idx, obj in enumerate(results.objects, 1):
            props = obj.properties
            print(f"{idx}. {props.get('name_title')} - ${props.get('category')}")

    finally:
        client.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weaviate Product Search CLI")
    subparsers = parser.add_subparsers(dest="command")

    # semantic search
    search_parser = subparsers.add_parser("search", help="Semantic product search")
    search_parser.add_argument("query", type=str, help="Search text")
    search_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    # list by category
    cat_parser = subparsers.add_parser("category", help="List products by category")
    cat_parser.add_argument("name", type=str, help="Category name")
    cat_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    # list by category
    title_parser = subparsers.add_parser("title", help="Semantic Search of Product Name")
    title_parser.add_argument("query", type=str, help="Category name")
    title_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    # list by category
    cat_parser = subparsers.add_parser("description", help="Semantic Search of Product Description")
    cat_parser.add_argument("query", type=str, help="Description Phrase")
    cat_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    args = parser.parse_args()

    if args.command == "search":
        semantic_search(args.query, args.top_k)
    elif args.command == "category":
        list_by_category(args.name, args.top_k)
    elif args.command == "title":
        semantic_search(args.query, args.top_k, "name_title")
    elif args.command == "description":
        semantic_search(args.query, args.top_k, "description")
    else:
        parser.print_help()
