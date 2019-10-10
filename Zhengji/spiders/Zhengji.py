import scrapy, re
from datetime import datetime
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from urllib.parse import parse_qs, urlparse
from Zhengji.items import ZhengJiItem


class ZhengJi(scrapy.Spider):
    name = 'ZhengJi'
    start_urls = ['http://35261646.com.hk/']

    def __init__(self):
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_opened(self, spider):
        spider.started_on = datetime.now()
        self.logger.info(f"Start time of spider: {spider.started_on}")

    def spider_closed(self, spider):
        spider.stopped_on = datetime.now()
        spider.worked_time = spider.stopped_on - spider.started_on
        self.logger.info(f"End time of spider: {spider.stopped_on} ")
        self.logger.info(f"Total time cost of spider: {spider.worked_time} ")

    def parse(self, response):
        cate_urls = response.css("div.box-category").xpath('ul/li/a/@href').extract()[2:4]
        for cate_url in cate_urls:
            meta = {'cate_urls': cate_url}
            yield scrapy.Request(cate_url, callback=self.parse_cate_pagination, meta=meta)

    def parse_cate_pagination(self, response):
        cate_url = response.meta['cate_urls']
        # get the url of last page if any
        last_page = response.css("div.pagination").xpath('div/a[contains(text(), ">|")]/@href').extract()
        if last_page:
            # start from page=2
            last_page_no = int(parse_qs(urlparse(last_page[0]).query)['page'][0])
            for i in range(1, last_page_no + 1):
                if i == 1:
                    yield scrapy.Request(cate_url, callback=self.parse_product, meta=response.meta)
                else:
                    url = f"{cate_url}&page={i}"
                    yield scrapy.Request(url, callback= self.parse_product, meta=response.meta)
        else:
            yield scrapy.Request(cate_url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        product_urls = response.css(" .product-list-item").xpath('div/a/@href').extract()
        for product_url in product_urls:
            yield scrapy.Request(product_url, callback=self.parse_product_info, meta=response.meta)

    def parse_product_info(self, response):
        item = ZhengJiItem()
        item["request_url"] = response.request.url
        item['product_id'] = int(parse_qs(urlparse(response.request.url).query)['product_id'][0])
        # extract only Chinese name
        cate_name = response.xpath('//span[@itemprop="title"]/text()').extract()[1]
        re_words = re.compile(u"[\u4e00-\u9fa5]+")
        # fix error: NoneType don't have attribute type
        item['product_category'] = re_words.search(cate_name, 0).group(0)

        # in jpg format
        item['product_desc'] = response.css(" #tab-description").xpath('p/img/@src').extract()

        left_pane  = response.css(" .product-info.split-60-40 .left .image")
        item['product_image'] = left_pane.xpath('a/@href').extract()[0]
        item['product_name'] = left_pane.xpath('a/@title').extract()[0]

        # error: index out of range
        right_pane = response.css(" .right .product-options")
        # fix error: list index out of range
        item['brand_name'] = right_pane.css(" .description").xpath('a/text()').extract()[0]

        price_old = right_pane.css(" .price").xpath('span[@class="price-old"]/text()').extract()
        price_old = float(re.search('[0-9.]+', price_old[0]).group(0))
        price_new = right_pane.css(" .price").xpath('span[@class="price-new"]/text()').extract()
        price_new = float(re.search('[0-9.]+', price_new[0]).group(0))
        item['price'] = {"price_new": price_new, "price_old": price_old}

        # discount if any
        product_discounts = []
        discounts = response.css(" .discount").extract()
        discounts = [discount.strip() for discount in discounts]
        if discounts:
            i = 0
            for discount in discounts:
                price = float(re.search('HKD[0-9.]+', discount).group(0)[3:])
                unit = int(re.search('[0-9]]', discount).group(0))
                product_discounts[i] = {"price": price, "unit": unit}
                i = i + 1
        item['discount'] = product_discounts

        yield item



