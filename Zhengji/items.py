# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ZhengjiItem(scrapy.Item):
    product_id = scrapy.Field()
    request_url = scrapy.Field()
    product_name = scrapy.Field()
    product_category = scrapy.Field()
    brand_name = scrapy.Field()
    price = scrapy.Field()
    discount = scrapy.Field()
    product_desc = scrapy.Field()
    product_image = scrapy.Field()
