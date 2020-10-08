import os
import csv
import time
from multiprocessing import Pool
from utils.csvWriter import csvWriter
from utils.split_list import splitList
from utils.loadConfig import load_config
from utils.get_more_topic import get_more_topic
from utils.get_query_info import word_get_query_info
from utils.get_repost_info import word_repost_relationship


# 参数为初始检索词列表，进程名
def word_spider():
    # 加载设置文件，获取数据输出路径和检索词
    config = load_config()
    hot_dir = config['hot_dir']
    topic_dir = config['topic_dir']
    repost_dir = config['repost_dir']
    process_num = config['process_num']
    one_word = config['one_word']
    searchlist = config['searchlist']

    # 记录载入检索词列表的次数
    epoch = 1

    while True:
        # 对每一个词爬取相关微博和各微博的转发关系
        for wd in searchlist:
            print(f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}]  EPOCH: {epoch}. Keyword: {wd}.')
            search_file = hot_dir + 'search_result_' + str(wd) + '.csv'
            repost_file = repost_dir + 'repost_Relationship_' + str(wd) + '.csv'
            # 创建两个写的对象,同时创建文件
            search_writer = csvWriter(search_file, search=True)
            repost_writer = csvWriter(repost_file, repost=True)

            # 获取该检索词的所有相关微博，至多能获取1000条
            # 因为Python不兼容多进程的日志，而之后repost需要多进程
            # 所以凡日志输出，都需要新开进程处理
            print(f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}]  Start searching keyword: {wd}.')
            p = Pool(1)
            p.apply_async(word_get_query_info, args=(wd, search_writer))
            p.close()
            p.join()
            print(f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}]  Finished searching keyword: {wd}.')

            # 获取相关微博id组成的列表
            raw_idList = search_writer.get_idList()
            # 分割待爬取转发关系的id，以便开启进程
            idList = splitList(raw_idList, process_num)
            # 需要临时目录来存储多个进程的文件
            temp = repost_dir + wd + '/'
            os.mkdir(temp)

            # 多进程爬取转发关系
            print(f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}]  Start crawling repost relationship...')
            p = Pool(process_num)
            for sublist in idList:
                p.apply_async(word_repost_relationship, args=(temp, sublist))
            p.close()
            p.join()

            # 整合中间文件成完整文件并去重
            repost_writer.merge_csv(temp)

            # 获取该词相关所有话题作为之后的检索词
            if one_word:
                break
            else:
                get_more_topic(wd, epoch, topic_dir)

        # 结束一轮检索爬取
        # 获取新检索词列表
        filename = topic_dir + 'Topics_' + str(epoch) + '.csv'
        with open(filename, 'r', encoding='utf-8-sig') as f:
            rows = csv.reader(f)
            searchlist = list(set([row[0].strip() for row in rows]))
        os.remove(filename)

        epoch += 1


if __name__ == '__main__':
    word_spider()
