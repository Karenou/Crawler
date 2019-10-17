# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import boto3
from datetime import datetime
from google.cloud import bigquery
import re
from scrapy.exceptions import DropItem
import simplejson as json
from zhengji.settings import config


class FilteringPipeline(object):

    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        if item.get("product_id") and item.get("product_name"):
            if item["product_id"] in self.ids_seen:
                dropped_info = dict(
                    item_id=item.get("product_id"),
                    item_name=item.get("product_name"),
                    item_url=item.get("request_url")
                )
                raise DropItem(f"duplicate item found: {dropped_info}")
            else:
                self.ids_seen.add(item["product_id"])
                return item
        else:
            dropped_info = dict(
                item_id=item.get("product_id"),
                item_name=item.get("product_name"),
                item_url=item.get("request_url")
            )
            raise DropItem(f"missing id or name: {dropped_info}")


class ZhengjiPipeline(object):

    def open_spider(self, spider):
        self.file = open(config["local"]["output_json"], "w")

    def close_spider(self, spider):
        self.file.close()

        # post the result to s3
        s3_resource = boto3.resource("s3")
        s3_resource.Bucket(config["aws"]["s3"]["bucket"]) \
            .upload_file(config["local"]["output_json"], config["aws"]["s3"]["filekey"])

        # post the fucking results to bigquery~
        for i in range(3):
            try:
                bq_client = bigquery.Client(project=config["gcp"]["project-id"])
                database_ref = bq_client.dataset(config["gcp"]["bigquery"]["database"])
                table_ref = database_ref.table(config["gcp"]["bigquery"]["table"])

                bq_schema = [
                    bigquery.SchemaField("_source", "STRING"),
                    bigquery.SchemaField("product_id", "STRING"),
                    bigquery.SchemaField("product_name", "STRING"),
                    bigquery.SchemaField("brand_name", "STRING"),
                    bigquery.SchemaField("product_desc", "STRING"),
                    bigquery.SchemaField("product_spec", "STRING"),
                    bigquery.SchemaField("_created_date", "TIMESTAMP"),
                    bigquery.SchemaField("product_image", "STRING"),
                    bigquery.SchemaField("request_url", "STRING"),
                    bigquery.SchemaField("price", "RECORD", mode="REPEATED",
                                         fields=(bigquery.SchemaField("price", "FLOAT"),
                                                 bigquery.SchemaField("CU_status", "STRING"),
                                                 bigquery.SchemaField("unit", "INTEGER"))),
                    bigquery.SchemaField("product_category", "RECORD", mode="REPEATED",
                                         fields=(bigquery.SchemaField("name", "STRING"),
                                                 bigquery.SchemaField("code", "STRING")))
                ]

                job_config = bigquery.LoadJobConfig()
                job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
                job_config.schema = bq_schema

                with open(config["local"]["output_json"], "rb") as json_file:
                    job = bq_client.load_table_from_file(json_file, table_ref, location="US", job_config=job_config)
                    job.result()
                break
            except:
                continue

    def process_item(self, item, spider):

        output = dict(
            product_id= item["product_id"],
            product_name=item["product_name"],
            brand_name=item["brand_name"],
            product_desc=item["product_desc"],
            product_image=item["product_image"],
            request_url=item["request_url"],
            product_category=item["product_category"],
            product_spec=item["product_spec"],
            price=item['price'],
            _source="ZHENGJI",
            _created_date=str(datetime.utcnow()),
        )

        # save line separated json object for next job
        line = json.dumps(output) + "\n"
        self.file.write(line)

        return output
