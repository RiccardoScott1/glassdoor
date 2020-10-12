# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


from glassdoor_scraper.items import CompanyInfo, Review
import json

class TutorialPipeline(object):
    def process_item(self, item, spider):
        return item


class JsonWriterPipeline(object):

    def open_spider(self, spider):
        self.fileCompanyInfo = open('data/CompanyInfo.jl', 'a')
        self.fileReviews = open('data/Reviews.jl', 'a')

    def close_spider(self, spider):
        self.fileCompanyInfo.close()
        self.fileReviews.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        if isinstance(item, CompanyInfo):
            self.fileCompanyInfo.write(line)
            return item
        elif isinstance(item, Review):
            self.fileReviews.write(line)
            return item
        else:
            return item