import scrapy, re
from datetime import datetime
from scrapy import signals
# from scrapy.xlib.pydispatch import dispatcher
from urllib.parse import parse_qs, urlparse
from sasa.items import SasaItem


class Sasa(scrapy.Spider):
    name = 'sasa'
    start_urls = ['https://hongkong.sasa.com/SasaWeb/eng/sasa/home.jsp']

    @classmethod
    def from_crawler(cls, crawler,*args, **kwargs):
        spider = super(sasa, cls).from_crawler(crawler, *args, **kwargs)
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
        download_slot = response.meta['download_slot']
        cate_urls = response.css("div.category_expand_item").xpath('a/@href').extract()
        for url in cate_urls:
            cate_url = download_slot + url
            meta = {'cate_url': cate_url}
            yield scrapy.Request(cate_url, callback=self.parse_cate_pagination, meta=meta)

    def parse_subcategory(self, response):
        subcate_urls = response.css("div.box_catalog div.content").xpath('dl/dt/a/@href').extract()
        for subcate_url in subcate_urls:
            meta = {'subcate_url': subcate_url}
            yield scrapy.Request(subcate_url, callback=self.parse_cate_pagination, meta=meta)

    def parse_cate_pagination(self, response):
        subcate_url = response.meta['subcate_url']
        url = f"{subcate_url}&page={1}"
        yield scrapy.Request(url, callback=self.parse_product, meta=response.meta)
        # get the url of last page if any
        page_urls = response.css("div.pages").xpath('a[string-length(text())>0]/@href').extract()
        if page_urls:
            for page_url in page_urls:
                download_slot = response.meta['download_slot']
                url = download_slot + page_url
                yield scrapy.Request(url, callback= self.parse_product, meta=response.meta)

    def parse_product(self, response):
        product_urls = response.css("div.box_list").xpath('ul/li/a[2]/@href').extract()
        for product_url in product_urls:
            download_slot = response.meta['download_slot']
            url = download_slot + product_url
            yield scrapy.Request(url, callback=self.parse_product_info, meta=response.meta)

    def parse_product_info(self, response):
        # if find empty url page, skip
        # content = response.css(" #content").xpath('h1/text()').extract()
        # if content:
        #     yield
        # else:
        item = SasaItem()
        item["request_url"] = response.request.url
        item['product_id'] = "SASA/" + parse_qs(urlparse(response.request.url).query)['itemno'][0]

        banner = response.css("div.margin div.location")
        item['brand_name'] = banner.xpath('a[contains(@href,"brand")]/text()').extract_first()
        # there are levels of category
        item['product_category'] = banner.xpath('a[contains(@href,"cate")]/text()').extract()[-1]
        # item['product_name'] = banner.xpath('b/text()').extract_first()

        left_pane = response.css("div.margin div.detail-info.mt-10 div.left")
        item['product_image'] = left_pane.xpath('div/img/@src').extract()

        right_pane = response.css("div.margin div.detail-info.mt-10 div.right")
        item['product_name'] = right_pane.css("div.title").xpath('a/span/text()').extract()[-1]

        content = right_pane.css("div.content").xpath('div/text()').extract()
        for element in content:
            if 'specification' in element:
                pos = element.find(':')
                item['product_spec'] = element[pos:]



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