import scrapy, re
from datetime import datetime
from scrapy import signals
# from scrapy.xlib.pydispatch import dispatcher
from urllib.parse import parse_qs, urlparse
from zhengji.items import ZhengJiItem


class ZhengJi(scrapy.Spider):
    name = 'ZhengJi'
    start_urls = ['http://35261646.com.hk/']

    @classmethod
    def from_crawler(cls, crawler,*args, **kwargs):
        spider = super(ZhengJi, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_opened(self, spider):
        spider.started_on = datetime.now()
        self.logger.info(f"Start time of spider: {spider.started_on}")

    def spider_closed(self, spider):
        spider.stopped_on = datetime.now()
        spider.worked_time = spider.stopped_on - spider.started_on
        self.logger.info(f"End time of spider: {spider.stopped_on} ")
        self.logger.info(f"Total time cost of spider: {spider.worked_time} ")

    def parse(self, response):
        # modify to change to extract different categories
        cate_urls = response.css("div.box-category").xpath('ul/li/a/@href').extract()[1:]
        for cate_url in cate_urls:
            meta = {'cate_url': cate_url}
            yield scrapy.Request(cate_url, callback=self.parse_cate_pagination, meta=meta)

    def parse_cate_pagination(self, response):
        cate_url = response.meta['cate_url']
        url = f"{cate_url}&page={1}"
        yield scrapy.Request(url, callback=self.parse_product, meta=response.meta)
        # get the url of last page if any
        last_page = response.css("div.pagination").xpath('div/a[contains(text(), ">|")]/@href').extract()
        if last_page:
            last_page_no = int(parse_qs(urlparse(last_page[0]).query)['page'][0])
            for i in range(2, last_page_no + 1):
                url = f"{cate_url}&page={i}"
                yield scrapy.Request(url, callback= self.parse_product, meta=response.meta)

    def parse_product(self, response):
        product_urls = response.css(" .product-list-item").xpath('div/a/@href').extract()
        for product_url in product_urls:
            yield scrapy.Request(product_url, callback=self.parse_product_info, meta=response.meta)

    def parse_product_info(self, response):
        # if find empty url page, skip
        content = response.css(" #content").xpath('h1/text()').extract()
        if content:
            yield
        else:
            item = ZhengJiItem()
            item["request_url"] = response.request.url
            item['product_id'] = "ZHENGJI/" + parse_qs(urlparse(response.request.url).query)['product_id'][0]
            cate_name = response.xpath('//span[@itemprop="title"]/text()').extract()[1]
            cn_cate_name = re.search('[\u4e00-\u9fa5]+', cate_name)
            if cn_cate_name is None:
                en_cate_name = re.search('[a-zA-Z]+', cate_name).group(0)
                item["product_category"] = [{"name": en_cate_name, "code": ""}]
            else:
                item["product_category"] = [{"name": cn_cate_name.group(0), "code": ""}]

            # in jpg format, some products don't have any info
            item['product_desc'] = response.css(" #tab-description").xpath('p/img/@src').extract_first()

            left_pane = response.css(" .product-info.split-60-40 .left .image")
            item['product_image'] = left_pane.xpath('a/@href').extract()[0]
            product_name = left_pane.xpath('a/@title').extract()[0]
            # store the unit and volume
            product_spec = re.search('[0-9]+ *[a-zA-Z]+ *x *[0-9]+', product_name)
            if product_spec is not None:
                item['product_spec'] = product_spec.group(0)
                pos = product_name.find(product_spec[0])
                item['product_name'] = product_name[0:pos-1]
            else:
                item['product_spec'] = ""
                item['product_name'] = product_name

            right_pane = response.css(" .right .product-options")
            # some products don't have brand_name
            brand_name = right_pane.css(" .description").xpath('a/text()').extract()
            if brand_name:
                item['brand_name'] = brand_name[0]
            else:
                item['brand_name'] = ""

            price_old = right_pane.css(" .price").xpath('span[@class="price-old"]/text()').extract()
            price_old = float(re.search('[0-9.]+', price_old[0]).group(0))
            price_new = right_pane.css(" .price").xpath('span[@class="price-new"]/text()').extract()
            price_new = float(re.search('[0-9.]+', price_new[0]).group(0))
            price_arr = [{"unit": 1, "CU_status": "normal", "price": price_new}, \
                             {"unit": 1, "CU_status": "original", "price": price_old}]

            # add discount to price if any
            discounts = response.css(" .discount::text").extract()
            discounts = [discount.strip() for discount in discounts]
            if discounts:
                for discount in discounts:
                    if discount:
                        price = float(re.search('HKD[0-9.]+', discount).group(0)[3:])
                        unit = int(re.search('[0-9]+', discount).group(0))
                        price_arr.append({"unit": unit, "CU_status": "normal", "price": price})
            item['price'] = price_arr

            yield item



