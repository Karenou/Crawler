import scrapy, re
from datetime import datetime
import scrapy import signal
from scrapy.xlib.pydispatch import dispatcher
from urllib.parse import parse_qs, urlparse
from Zhengji.items import ZhengjiItem


class Zhengji(Spider):
    name = 'Zhengji'
    start_url = ['http://35261646.com.hk/']

    def __init__(self):
        dispatcher.connect(self.sipder_opened, signal.spider_opened)
        dispatcher.connect(self.sipder_closed, signal.spider_closed)

    def spider_opened(self, spider):
        spider.started_on = datetime.now()
        self.logger.info(f"Start time of spider: {spider.started_on}")

    def spider_closed(self, spider):
        spider.stopped_on = datetime.now()
        spider.worked_time = spider.stopped_on - spider.started_on
        self.logger.info(f"End time of spider: {spider.stopped_on} ")
        self.logger.info(f"Total time cost of spider: {spider.worked_time} ")

    def parse(self, response):
        cate_urls = response.css("div.box-category").xpath('ul/li/a/@href').extract()[1:]
        for cate_url in cate_urls:
            meta = {"cate_urls": cate_url}
            yield scrapy.Request(cate_url, callback=self.parse_cate_pagination, meta = meta)

    def parse_cate_pagination(self, response):
        cate_url = response.meta
        # get the url of last page if any
        last_page = response.css("div.pagination").xpath('div/a[contains(text(), ">|")]/@href').extract()
        if not last_page:
            last_page_no = int(parse_qs(urlparse(last_page).query)['page'][0])
            for i in range(2, last_page_no + 1):
                url = f"{cate_url}&page={i}"
                yield scrapy.Request(url, callback= self.parse_product, meta = response.meta)
        else:
            yield scrapy.Request(cate_url, callback=self.parse_product, meta = response.meta)

    def parse_product(self, response):
        product_urls = response.css("div.product-wrapper").xpath('div/a/@href').extract()
        for product_url in product_urls:
            yield scrapy.Request(product_url, callback=self.parse_product_info, meta=response.meta)

    def parse_product_info(self, response):



