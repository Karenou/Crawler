import scrapy, re
from datetime import datetime
from scrapy import signals
# from scrapy.xlib.pydispatch import dispatcher
from urllib.parse import parse_qs, urlparse
from sasa.items import SasaItem


class Sasa(scrapy.Spider):
    name = 'sasa'
    start_urls = ['https://hongkong.sasa.com/SasaWeb/tch/sasa/home.jsp?cm_re=top_logo']

    @classmethod
    def from_crawler(cls, crawler,*args, **kwargs):
        spider = super(Sasa, cls).from_crawler(crawler, *args, **kwargs)
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
            cate_url = 'http://' + download_slot + url
            meta = {'cate_url': cate_url}
            yield scrapy.Request(cate_url, callback=self.parse_subcategory, meta=meta)

    def parse_subcategory(self, response):
        subcate_urls = response.css("div.box_catalog div.content").xpath('dl/dt/a/@href').extract()
        for subcate_url in subcate_urls:
            url = 'https://web1.sasa.com' + subcate_url
            meta = {'subcate_url': url}
            yield scrapy.Request(url, callback=self.parse_cate_pagination, meta=meta)

    def parse_cate_pagination(self, response):
        subcate_url = response.meta['subcate_url']
        url = f"{subcate_url}&page={1}"
        yield scrapy.Request(url, callback=self.parse_product, meta=response.meta)
        # get the url of last page if any
        page_urls = response.css("div.pages").xpath('a[string-length(text())>0]/@href').extract()
        if page_urls:
            for page_url in page_urls:
                url = 'https://web1.sasa.com' + page_url
                yield scrapy.Request(url, callback= self.parse_product, meta=response.meta)

    def parse_product(self, response):
        product_urls = response.css("div.box_list").xpath('ul/li/a[2]/@href').extract()
        for product_url in product_urls:
            url = 'https://web1.sasa.com' + product_url
            yield scrapy.Request(url, callback=self.parse_product_info, meta=response.meta)

    def parse_product_info(self, response):
        item = SasaItem()
        item["request_url"] = response.request.url
        item['product_id'] = "SASA/" + parse_qs(urlparse(response.request.url).query)['itemno'][0]

        banner = response.css("div.margin div.location")
        item['brand_name'] = banner.xpath('a[contains(@href,"brand")]/text()').extract_first()
        # there are levels of category
        product_cate = banner.xpath('a[contains(@href,"cate")]/text()').extract()[-1]
        code_url = banner.xpath('a[contains(@href,"cate")]/@href').extract()[-1]
        code = parse_qs(urlparse(code_url).query)['categoryId'][0]
        item['product_category'] = [{"name": product_cate, "code": code}]

        left_pane = response.css("div.margin div.detail-info.mt-10 div.left")
        item['product_image'] = left_pane.xpath('div/img/@src').extract_first()

        right_pane = response.css("div.margin div.detail-info.mt-10 div.right")
        item['product_name'] = right_pane.css("div.title").xpath('a/span/text()').extract()[-1]

        content = right_pane.css("div.content").xpath('div/text()').extract()
        product_dict = {}
        for element in content:
            pos = element.find('：')
            if pos != -1:
                key = element[:pos].replace(" ", "")
                product_dict[key] = element[(pos+1):].strip().replace(" ", "")

        if '規格' in product_dict.keys():
            item['product_spec'] = product_dict['規格']
        else:
            item['product_spec'] = ''

        price_arr = []
        price_now = right_pane.css("div.content").xpath('div/big/text()').extract_first()
        price_now = float(re.search('[0-9.0]+', price_now).group(0))
        if 'RRP' in product_dict.keys():
            RRP = float(re.search('[0-9.0]+',product_dict['RRP']).group(0))
            price_arr.append({'unit': 1, 'CU_status': 'original', 'price': RRP})
            price_arr.append({'unit': 1, 'CU_status': 'discount', 'price': price_now})
        else:
            price_arr.append({'unit': 1, 'CU_status': 'normal', 'price': price_now})

        item['price'] = price_arr

        product_desc = response.css("div#Detail div.right div.detail-item#chapter-2 div.content")\
            .xpath('p/text()').extract()

        separator = ' '
        item['product_desc'] = separator.join(product_desc)

        yield item