# -*- coding: utf-8 -*-
import scrapy
import json
from youtube.items import ChannelItem
# from pyquery import PyQuery as pq

class YouTuBeScrapy(scrapy.Spider):
    name = "youtube"
    start_urls = ["https://www.youtube.com/"]
    allowed_domains = ["youtube.com"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        url = "https://www.youtube.com/results?search_query=coffee&pbj=1"
        html_text = response.text
        # 从response中获取一些请求头参数， 否则接下来的请求拿不到数据
        sts_start = html_text.find('"sts":') + len('"sts":')
        end = html_text.find(',', sts_start)
        sts = html_text[sts_start: end]
        if "}" in sts:
            sts = sts.split("}")[0]
        page_label_start = html_text.find("{window.ytplayer = {};ytcfg.set(") + len("{window.ytplayer = {};ytcfg.set(")
        end = html_text.find(");", page_label_start)
        page_label_dict = json.loads(html_text[page_label_start: end])
        page_label = page_label_dict['PAGE_BUILD_LABEL']
        page_cl = str(page_label_dict["PAGE_CL"])
        client_version = page_label_dict["INNERTUBE_CONTEXT_CLIENT_VERSION"]
        checksum = page_label_dict["VARIANTS_CHECKSUM"]
        XSRF_TOKEN = page_label_dict["XSRF_TOKEN"]
        update_headers = {
            "X-YouTube-STS": sts,
            "X-YouTube-Page-Label": page_label,
            "X-YouTube-Variants-Checksum": checksum,
            "X-YouTube-Page-CL": page_cl,
            "X-SPF-Referer": "https://www.youtube.com/",
            "X-YouTube-Utc-Offset": "480",
            "X-YouTube-Client-Name": "1",
            "X-SPF-Previous": "https://www.youtube.com/",
            "X-YouTube-Client-Version": client_version,
            "Accept": "*/*",
            "Referer": "https://www.youtube.com/"}
        yield scrapy.Request(url, callback=self.parseVideoUrl, headers=update_headers, meta={"headers": update_headers})

    def parseVideoUrl(self, response):
        #在返回结果里获取到视频的url
        result = json.loads(response.body.decode("utf-8"))
        video_url = result[1]["response"]["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
            "sectionListRenderer"]["subMenu"]["searchSubMenuRenderer"]["groups"][1]["searchFilterGroupRenderer"][
            "filters"][0]["searchFilterRenderer"]["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"]
        url = "https://www.youtube.com" + video_url + "&pbj=1"
        yield scrapy.Request(url, callback=self.parseVideo, meta={"headers": response.meta["headers"], "url": url, "start": True}, headers=response.meta["headers"])

    def parseVideo(self, response):
        a = 1
        start = response.meta["start"]
        start_url = response.meta["url"]
        next_dict = json.loads(response.body.decode("utf-8"))
        print(json.dumps(next_dict))
        token = next_dict[1]["xsrf_token"]
        if start:
            continuation = next_dict[1]["response"]["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
                "sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["continuations"][0]["nextContinuationData"][
                "continuation"]
            ictc = next_dict[1]["response"]["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
                "sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["continuations"][0]["nextContinuationData"][
                "clickTrackingParams"]
            next_url = start_url + "&ctoken=" + continuation + "&continuation=" + continuation + "&itct=" + ictc
            contents = next_dict[1]["response"]["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
                "sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]
            for content in contents:
                if "searchPyvRenderer" in content:
                    searchPyvRenderer = content["searchPyvRenderer"]
                    if "ads" in searchPyvRenderer:
                        longBylineText_url = searchPyvRenderer["ads"][0]["promotedVideoRenderer"]["longBylineText"]["runs"][0]["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"]
                        username = searchPyvRenderer["ads"][0]["promotedVideoRenderer"]["longBylineText"]["runs"][0]["text"]
                elif "videoRenderer" in content:
                    videoRenderer = content["videoRenderer"]
                    longBylineText_url = videoRenderer["longBylineText"]["runs"][0]["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"]
                    username = videoRenderer["longBylineText"]["runs"][0]["text"]
                else:
                    continue
                item = ChannelItem()
                item["username"] = username
                item["channel"] = longBylineText_url
                yield item
            print(json.dumps(contents))
            yield scrapy.FormRequest(next_url, callback=self.parseVideo,meta={"headers": response.meta["headers"], "url": start_url, "start": False},headers=response.meta["headers"], formdata={"session_token": token})
        else:
            contents = next_dict[1]["response"]["continuationContents"]["itemSectionContinuation"]["contents"]
            print(json.dumps(contents))
            for content in contents:
                if "searchPyvRenderer" in content:
                    searchPyvRenderer = content["searchPyvRenderer"]
                    if "ads" in searchPyvRenderer:
                        longBylineText_url = searchPyvRenderer["ads"][0]["promotedVideoRenderer"]["longBylineText"]["runs"][0]["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"]
                        username = searchPyvRenderer["ads"][0]["promotedVideoRenderer"]["longBylineText"]["runs"][0]["text"]
                elif "videoRenderer" in content:
                    videoRenderer = content["videoRenderer"]
                    longBylineText_url = videoRenderer["longBylineText"]["runs"][0]["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"]
                    username = videoRenderer["longBylineText"]["runs"][0]["text"]
                else:
                    continue
                item = ChannelItem()
                item["username"] = username
                item["channel"] = longBylineText_url
                yield item
            itemSectionContinuation = next_dict[1]["response"]["continuationContents"]["itemSectionContinuation"]
            token = next_dict[1]["xsrf_token"]
            if "continuations" in itemSectionContinuation:
                continuation = \
                next_dict[1]["response"]["continuationContents"]["itemSectionContinuation"]["continuations"][0][
                    "nextContinuationData"]["continuation"]
                ictc = next_dict[1]["response"]["continuationContents"]["itemSectionContinuation"]["continuations"][0][
                    "nextContinuationData"]["clickTrackingParams"]
                next_url = start_url + "&ctoken=" + continuation + "&continuation=" + continuation + "&itct=" + ictc
                yield scrapy.FormRequest(next_url, callback=self.parseVideo, meta={"headers": response.meta["headers"],"url": start_url, "start": False}, headers=response.meta["headers"], formdata={"session_token": token})
