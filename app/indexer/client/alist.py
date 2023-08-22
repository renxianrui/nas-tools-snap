import json
import re
import time
from urllib import request, parse

import requests

from app.filter import Filter
from app.helper import IndexerConf, ProgressHelper
from app.media import Media
from app.media.meta import MetaInfo
from app.utils import StringUtils
from app.utils.types import IndexerType, SearchType, MediaType
import log
import datetime

from config import Config


class Alist():
    schema = "jackett"
    _client_config = {}
    index_type = IndexerType.ALIST.value
    _password = None
    media = None

    _indexer=IndexerConf(datas={
        'id':'alsit',
        'name':'Alist',
        'domain': Config().get_config("alist").get('host'),

    },public=True,pri=100)

    def __init__(self, config=None):
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.host = 'http://192.168.31.186:5678'
        self.media=Media()
        self.filter = Filter()
        self.progress = ProgressHelper()

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.index_type] else False

    def search_by_keyword(self,
               key_word,
               filter_args: dict,
               match_media,
               in_from: SearchType):

        """
               根据关键字多线程检索
               """
        if  not key_word:
            return None
        if filter_args is None:
            filter_args = {}
        # 计算耗时
        start_time = datetime.datetime.now()
        log.info(f"【{self.index_type}】开始检索： ...")
        # 特殊符号处理
        search_word = StringUtils.handler_special_chars(text=key_word,
                                                        replace_word=" ",
                                                        allow_space=True)

        result_array = self.search(search_word)
        if len(result_array) == 0:
            log.warn(f"【{self.index_type}】 未检索到数据")
            return []
        else:
            log.warn(f"【{self.index_type}】 返回数据：{len(result_array)}")
        # return result_array

        return self.filter_search_results(result_array=result_array,
                                              order_seq=100, # alist优先级
                                              indexer=self._indexer,
                                              filter_args=filter_args,
                                              match_media=match_media,
                                              start_time=start_time)

    def post(self, url, data) -> (bool, dict):
        req_json = {}
        error_number = 0
        while True:
            status_code = 0
            try:
                req = requests.post(url=url, data=json.dumps(data), headers=self.headers, timeout=15)
                status_code = req.status_code
                req_json = req.json()
                req.close()
            except:
                pass

            if status_code == 200:
                break
            elif error_number > 2:
                break
            else:
                error_number += 1
                time.sleep(1)

        if status_code == 200:
            return True, req_json
        else:
            return False, req_json

    def search(self, keyword):
        result_url = []
        url = self.host + "/search?box=%s&type=%s&url=" % (keyword, "video")
        response = request.urlopen(parse.quote(url, safe='/:?=&'))
        result = response.read().decode('utf-8')
        print(result)
        matchs = re.findall('<a\s+href=(/[^>]+)>', result)
        if(matchs):
            for match in matchs:
                result_url+=self.get_list(match)
        return result_url


    def get_list(self, path):
        result_url = []
        url = self.host + "/api/fs/list"
        data = {"path": path, "password": "", "page": 1, "per_page": 0, "refresh": False}
        file_list = []
        error_number = 0
        while True:
            req_type, req_json = self.post(url=url, data=data)
            if req_type is False:
                return result_url
            elif req_json.get("code") == 200:
                break
            elif error_number > 2:
                break
            else:
                print(req_json)
                error_number += 1
                time.sleep(2)
        if req_json.get("data") is None:
            return result_url
        content = req_json.get("data")["content"]
        if content is None:
            return result_url
        for file_info in content:
            if file_info["is_dir"] is True:
                file_download_url = path + "/" + file_info["name"]
                print("dir", file_download_url)
                file_list.append({"is_dir": True, "path": file_download_url})
            else:
                file_download_url = self.host + "/d" + path + "/" + file_info["name"]
                # print("file", file_download_url)
                sign = file_info.get("sign")
                if sign is not None:
                    file_download_url = file_download_url + "?sign=" + sign
                file_list.append(
                    {"is_dir": False, "url": file_download_url, "path": path, "name": file_info["name"],
                     "size": file_info["size"]})

        for file in file_list:
            if file["is_dir"] is True:
                self.get_list(file["path"])
            else:
                # D:\download 文件下载的存储地址
                print(file["url"])
                result_url.append({
                    'index_id': 'alist',
                    'indexer': 'Alist',
                    'title': file["name"],
                    'enclosure': file["url"],
                    'description': '',
                    'size': file["size"],
                    'seeders': '100',
                    'peers': '100',
                    'freeleech': True,
                    'downloadvolumefactor': '0',
                    'uploadvolumefactor': '1',
                    'page_url': '',
                    'imdbid': ''

                })
        return result_url

    def filter_search_results(self, result_array: list,
                              order_seq,
                              indexer,
                              filter_args: dict,
                              match_media,
                              start_time):
        """
        从检索结果中匹配符合资源条件的记录
        """
        ret_array = []
        index_sucess = 0
        index_rule_fail = 0
        index_match_fail = 0
        index_error = 0
        for item in result_array:
            # 这此站标题和副标题相反
            torrent_name = item.get('title')
            description = item.get('description')

            if not torrent_name:
                index_error += 1
                continue
            enclosure = item.get('enclosure')
            size = item.get('size')
            seeders = item.get('seeders')
            peers = item.get('peers')
            page_url = item.get('page_url')
            uploadvolumefactor = round(float(item.get('uploadvolumefactor')), 1) if item.get(
                'uploadvolumefactor') is not None else 1.0
            downloadvolumefactor = round(float(item.get('downloadvolumefactor')), 1) if item.get(
                'downloadvolumefactor') is not None else 1.0
            imdbid = item.get("imdbid")
            # 全匹配模式下，非公开站点，过滤掉做种数为0的
            if filter_args.get("seeders") and not indexer.public and str(seeders) == "0":
                log.info(f"【{self.index_type}】{torrent_name} 做种数为0")
                index_rule_fail += 1
                continue
            # 识别种子名称
            meta_info = MetaInfo(title=torrent_name, subtitle=description)
            if not meta_info.get_name():
                log.info(f"【{self.index_type}】{torrent_name} 无法识别到名称")
                index_match_fail += 1
                continue
            # 大小及促销等
            meta_info.set_torrent_info(size=size,
                                       imdbid=imdbid,
                                       upload_volume_factor=uploadvolumefactor,
                                       download_volume_factor=downloadvolumefactor)

            # 先过滤掉可以明确的类型
            if meta_info.type == MediaType.TV and filter_args.get("type") == MediaType.MOVIE:
                log.info(
                    f"【{self.index_type}】{torrent_name} 是 {meta_info.type.value}，不匹配类型：{filter_args.get('type').value}")
                index_rule_fail += 1
                continue
            # 检查订阅过滤规则匹配
            match_flag, res_order, match_msg = True,100,""
            if not match_flag:
                log.info(f"【{self.index_type}】{match_msg}")
                index_rule_fail += 1
                continue
            # 识别媒体信息
            if not match_media:
                # 不过滤
                media_info = meta_info
            else:
                # 0-识别并模糊匹配；1-识别并精确匹配
                if meta_info.imdb_id \
                        and match_media.imdb_id \
                        and str(meta_info.imdb_id) == str(match_media.imdb_id):
                    # IMDBID匹配，合并媒体数据
                    media_info = self.media.merge_media_info(meta_info, match_media)
                else:
                    # 查询缓存
                    cache_info = self.media.get_cache_info(meta_info)
                    if match_media \
                            and str(cache_info.get("id")) == str(match_media.tmdb_id):
                        # 缓存匹配，合并媒体数据
                        media_info = self.media.merge_media_info(meta_info, match_media)
                    else:
                        # 重新识别
                        media_info = self.media.get_media_info(title=torrent_name, subtitle=description, chinese=False)
                        if not media_info:
                            log.warn(f"【{self.index_type}】{torrent_name} 识别媒体信息出错！")
                            index_error += 1
                            continue
                        elif not media_info.tmdb_info:
                            log.info(
                                f"【{self.index_type}】{torrent_name} 识别为 {media_info.get_name()} 未匹配到媒体信息")
                            index_match_fail += 1
                            continue
                        # TMDBID是否匹配
                        if str(media_info.tmdb_id) != str(match_media.tmdb_id):
                            log.info(
                                f"【{self.index_type}】{torrent_name} 识别为 {media_info.type.value} {media_info.get_title_string()} 不匹配")
                            index_match_fail += 1
                            continue
                        # 合并媒体数据
                        media_info = self.media.merge_media_info(media_info, match_media)
                # 过滤类型
                if filter_args.get("type"):
                    if (filter_args.get("type") == MediaType.TV and media_info.type == MediaType.MOVIE) \
                            or (filter_args.get("type") == MediaType.MOVIE and media_info.type == MediaType.TV):
                        log.info(
                            f"【{self.index_type}】{torrent_name} 是 {media_info.type.value}，不是 {filter_args.get('type').value}")
                        index_rule_fail += 1
                        continue
                # 洗版
                if match_media.over_edition:
                    # 季集不完整的资源不要
                    if media_info.type != MediaType.MOVIE \
                            and media_info.get_episode_list():
                        log.info(f"【{self.index_type}】{media_info.get_title_string()}{media_info.get_season_string()} "
                                 f"正在洗版，过滤掉季集不完整的资源：{torrent_name} {description}")
                        continue
                    # 检查优先级是否更好
                    if match_media.res_order \
                            and int(res_order) <= int(match_media.res_order):
                        log.info(
                            f"【{self.index_type}】{media_info.get_title_string()}{media_info.get_season_string()} "
                            f"正在洗版，已洗版优先级：{100 - int(match_media.res_order)}，"
                            f"当前资源优先级：{100 - int(res_order)}，"
                            f"跳过低优先级或同优先级资源：{torrent_name}"
                        )
                        continue
            # 检查标题是否匹配季、集、年
            if not self.filter.is_torrent_match_sey(media_info,
                                                    filter_args.get("season"),
                                                    filter_args.get("episode"),
                                                    filter_args.get("year")):
                log.info(
                    f"【{self.index_type}】{torrent_name} 识别为 {media_info.type.value} {media_info.get_title_string()} {media_info.get_season_episode_string()} 不匹配季/集/年份")
                index_match_fail += 1
                continue

            # 匹配到了
            log.info(
                f"【{self.index_type}】{torrent_name} {description} 识别为 {media_info.get_title_string()} {media_info.get_season_episode_string()} 匹配成功")
            media_info.set_torrent_info(site=indexer.name,
                                        site_order=order_seq,
                                        enclosure=enclosure,
                                        res_order=res_order,
                                        filter_rule=filter_args.get("rule"),
                                        size=size,
                                        seeders=seeders,
                                        peers=peers,
                                        description=description,
                                        page_url=page_url,
                                        upload_volume_factor=uploadvolumefactor,
                                        download_volume_factor=downloadvolumefactor)
            if media_info not in ret_array:
                index_sucess += 1
                ret_array.append(media_info)
            else:
                index_rule_fail += 1
        # 循环结束
        # 计算耗时
        end_time = datetime.datetime.now()
        log.info(
            f"【{self.index_type}】{indexer.name} 共检索到 {len(result_array)} 条数据，过滤 {index_rule_fail}，不匹配 {index_match_fail}，错误 {index_error}，有效 {index_sucess}，耗时 {(end_time - start_time).seconds} 秒")
        self.progress.update(ptype='search',
                             text=f"{indexer.name} 共检索到 {len(result_array)} 条数据，过滤 {index_rule_fail}，不匹配 {index_match_fail}，错误 {index_error}，有效 {index_sucess}，耗时 {(end_time - start_time).seconds} 秒")
        return ret_array