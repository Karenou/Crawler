# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import boto3
from datetime import datetime
# from google.cloud import bigquery
import re
from scrapy.exceptions import DropItem
import simplejson as json
# from Zhengji.settings import config

class ZhengJiPipeline(object):
    def process_item(self, item, spider):
        return item
