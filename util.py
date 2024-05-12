import requests
import json
import re
import os
def bili_download(Path,download_location,part_num=None,title=None):
    default_download_text = '在此输入b站视频链接\n如果是小程序，请复制视频号'
    default_part_text = "在此输入要下载的分p号（视频未分p请忽略）"
    default_title_text = "在此输入想另取的标题（没有请忽略）"

    default_error_text = ["网址错误，请按规范输入","网址为空，请重新输入"]

    if Path == default_download_text or Path in default_error_text:
        # 对输入path进行校验
        return {'code':-1,'title':None} # 返回-1表示下载异常
    Path = Path.replace("？","?")

    if Path[:2] == "BV" and len(Path) == 12:
        Path = 'https://www.bilibili.com/video/'+ Path

    if part_num ==default_part_text:
        pass
    else:
        # 先检查path有没有
        if '?p=' in Path:
            # 如果有，就更换
            Path = re.sub("(?<=p=)\d+", part_num, Path)
        else:
            # 如果没有，就加上
            Path = Path+f"?p={part_num}"

    headers = {"referer": "https://www.bilibili.com",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
               }
    try:
        response = requests.get(url=Path, headers=headers)
    except:
        return {'code':-1,'title':None} # 返回-1表示下载异常
    # 返回响应状态码：<Response [200]>
    # print("返回200，则网页请求成功：", response)
    # .text获取网页源代码
    # print(response.text)
    if response.status_code != 200:
        return {'code':-1,'title':None} # 返回-1表示下载异常

    # 提取视频标题
    # 调用 re 的 findall 方法，去response.text中匹配我们要的标题
    # 正则表达式提取的数据返回的是一个列表，用[0]从列表中取值
    text = response.text
    # h1 data-title不适用于多p，下面两个适用多p
    # title = re.findall('<h1 data-title="(.*?)"', text)[0]
    if title == default_title_text or title == '':
        title = re.findall('<meta data-vue-meta="true" itemprop="name" name="title" content="(.*?)_哔哩哔哩_bilibili', text)[0]
        # <meta data-vue-meta="true" itemprop="name" name="title" content="
        # <meta data-vue-meta="true" property="og:title" content = "
        # 如果标题里有[\/:*?<>|]特殊字符，直接删除
        title = re.sub(r"[\/:*?<>|]", "", title).strip()
    else:
        pass
    # print("视频标题为：", title)
    html_data = re.findall('<script>window.__playinfo__=(.*?)</script>', response.text)[0]
    # html_data是字符串类型，将字符串转换成字典
    json_data = json.loads(html_data)
    # json_dicts = json.dumps(json_data, indent=4)
    # video_url = json_data["data"]["dash"]["video"][0]["baseUrl"]
    # print("视频画面地址为：", video_url)
    audio_url = json_data["data"]["dash"]["audio"][0]["baseUrl"]
    # print("音频地址为：", audio_url)

    # video_content = requests.get(url=video_url,headers=headers).content
    audio_response = requests.get(url=audio_url, headers=headers)
    audio_content = audio_response.content
    # content_type = requests.get(url=audio_url, headers=headers).headers.get('Content-Type')
    # print(content_type)
    # 创建mp4文件，写入二进制数据
    # with open(title + ".mp4", mode="wb") as f:
    #     f.write(video_content)
    # with open("./map3/"+title + ".mp3", mode="wb") as f:
    with open(os.path.join(download_location,title+".m4a"), mode="wb") as f:
        f.write(audio_content)
    # print("数据写入成功！")
    return {'code':1,
            'title':f'{title}'}


def list_files_in_directory(dir_path):
    # 获取目录下的所有文件名/文件夹名
    names = os.listdir(dir_path)
    # 把文件名拼接成完整的路径，然后筛选出所有文件
    files = [name[:-4] for name in names if os.path.isfile(os.path.join(dir_path, name))]
    # 排序， 新的文件在前
    files.sort(key=lambda x: os.path.getmtime(os.path.join(dir_path, x+".m4a")), reverse=True)
    return files
if __name__ == '__main__':
    import mutagen
    # from pydub import AudioSegment
    # Path = 'BV1wP411c77n？p=1'
    # bili_download(Path,"./mp3downloadCC")
    # mp3s = list_files_in_directory(os.path.abspath("./mp3download/"))
    # path = os.path.join(os.path.abspath("./mp3download/"), mp3s[0])
    # print(mp3s)
    # print(path)

    # Load m4a file
    # audio = AudioSegment.from_file(path, format="mp3")
    # Or convert to wav
    # audio.export('path_to_output_file.wav', format="wav")

    pass
    # url = 'https://www.bilibili.com/video/BV19Y4y1b71e?p=4&vd_source=af85484aeda15b2561214ea284dc02ba'
    # part_num='100'
    # new_url= re.sub("(?<=p=)\d+", part_num, url)
    # print(new_url)
