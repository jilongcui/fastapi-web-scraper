# tasks.py

import aiohttp
import asyncio
import time
import random
import os
import base64
import logging
import sys
from bs4 import BeautifulSoup
from urllib.parse import unquote
from app.logs import get_logger
from fastapi import FastAPI, HTTPException, Depends
from models.user import User  # 从models导入用户模型
from app.database import get_discussion_collection  # 从app导入数据库函数

# 获取一个特定的 logger 实例
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# StreamHandler für die Konsole
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

province = "国家"

async def fetch_captcha_svg(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                svg_data = await response.text()
                # logger.info(f"Fetched SVG: {svg_data}")  # 打印前100个字符以示例
                return svg_data
            else:
                logger.info(f"Failed to fetch SVG, status code: {response.status}")
                return None
            
# def image2Code2(imageUrl):
#     api_endpoint =f"https://mianshi.xiaohe.biz/api/interview-set/svg2Answer"
#     headers = {
#         # 'Authencation': f'{authToken}',
#         'Content-Type': 'application/json'
#     }
#     response = requests.post(api_endpoint, json={"imageUrl": imageUrl},headers=headers)
#     answer = None;
#     code = None
#     if (response.status_code == 200 or response.status_code == 201):
#         code = response.json().get("code", {})
#         if code == 200:
#             data = response.json().get("data", {})
#             answer = data.get("answer")

#     return data

async def image2Code(imageUrl):
    api_endpoint = "https://mian.xiaohe.biz/api/interview-set/svg2Answer"
    headers = {
        # 'Authentication': f'{authToken}',  # 确保替换为你的真实认证令牌
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(api_endpoint, json={"imageUrl": imageUrl}, headers=headers) as response:
            data = {}
            if response.status in (200, 201):
                # 如果返回状态码是200或201，处理响应内容
                logger.info("Request successful")
                data = await response.json()  # 假设服务器返回JSON格式数据
                code = data.get("code", {})
                if code == 200:
                    data = data.get("data", {})
                else:
                    logger.info(f"Request failed with status code: {response.status}")
            return data
# 定义API端点和图像URL

imageUrl = "your_image_url_here"


async def getDecodedUrls(paperId:str) -> dict:
    # 抓取svgStr
    url = "https://www.gkzenti.cn/captcha/math"
    timestamp = int(time.time())
    headers = {
        'Accept': "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        # 'Cookie': "connect.sid=s%3AFIZCYvlp4vhfk4l5eEq9rr74JCd2an67.uP2a3PFUS8LNC6LVfVaEu2XoG27NIIymPDducAD%2BM48; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1732881600; HMACCOUNT=1A150266D1AAAB30; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; province=%E5%9B%BD%E8%80%83; Hm_lpvt_db5c56a1da081947699f2e5bece459c7=1734586863",
        # "Cookie": f"connect.sid=s%3AasmGihKKO8OTgnFL2y_LgZmYVtts86x6.bbnOMAmmxvMpdGk7ctgHBdB7W4CTwE47z0Ku0x9e9xA; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734590397; HMACCOUNT=96C839E210B265AA; province=%E5%9B%BD%E8%80%83; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        # "Cookie": f"connect.sid=s%3Ae2VDDxSsjro9jpjIo6xX-b2ZgyS34FQN.GeKw6EjEaMKPbEBIJ3C1ldh5jRuoAcBvbTEqYUuYwN0; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734658177; HMACCOUNT=C3C8CCD265B20BCC; cls=%E7%94%B3%E8%AE%BA; province=%E5%9B%BD%E8%80%83; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        "Cookie": f"connect.sid=s%3Ae2VDDxSsjro9jpjIo6xX-b2ZgyS34FQN.GeKw6EjEaMKPbEBIJ3C1ldh5jRuoAcBvbTEqYUuYwN0; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734658177; HMACCOUNT=C3C8CCD265B20BCC; cls=%E7%94%B3%E8%AE%BA; province=%E6%B5%99%E6%B1%9F; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 QuarkPC/1.10.0.169"
    }
    headers['Referer'] = f"https://www.gkzenti.cn/paper/{paperId}"
    svgStr = await fetch_captcha_svg(url, headers)
    # 将转义字符移除
    svg_string = svgStr.replace('\"', '"')

    # 将修正后的SVG字符串编码为UTF-8字节
    svg_bytes = svg_string.encode('utf-8')
    
    # 对字节进行Base64编码
    base64_encoded_svg = base64.b64encode(svg_bytes).decode('utf-8')

    # 创建Data URI格式
    data_uri = f'data:image/svg+xml;charset=utf-8;base64,{base64_encoded_svg}'
    
    # 假设image2Answer是在其他地方定义的函数，用于处理encoded data和authentication token。
    data = await image2Code(data_uri)
    code = data.get("answer")
    code = int(code)
    explanUrl = f"https://www.gkzenti.cn/explain/{paperId}?mathcode={code}"
    return explanUrl

import re
def getTitleInfo(province, title):
    # 定义正则表达式模式，忽略月份
    # pattern = r'(?P<year>\d{4})年(?:\d{1,2})月\d{1,2}日(?P<department>.*?)面试'
    pattern = r'(?P<year>\d{4})年'
    # 解析每个主题
    title = title.strip().replace("上午", "").replace("下午", "")
    title = title.replace("（网友回忆版）", "")
    logger.info(title)

    match = re.search(pattern, title)
    if match:
        year = match.group('year')
        # department = match.group('department')
        department = province
        logger.info(f"主题: {title}")
        logger.info(f"  年份: {year}")
        logger.info(f"  省份: {province}")
        logger.info(f"  单位: {department}\n")
        return year, department
    return None, None

async def replace_image_urls(markdown_text, authToken=""):
    # 定义正则表达式来匹配 !img[](url)
    # pattern = r'!\[\]\(([^)]+)\)'
    # pattern = r"//upload\.gkzenti\.cn/[\w\d]+/[\w\d]+\.(png|jpg)"
    pattern = r"//upload\.gkzenti\.cn/\w+/\w+\.(?:png|jpg)"
    # pattern = r"//upload\.gkzenti\.cn/\w+/\w+\.(png|jpg)"
    api_endpoint ="https://mian.xiaohe.biz/api/common/uploadByUrl"
    headers = {
        # 'Authorization': f'Bearer {authToken}',
        'Content-Type': 'application/json'
    }
    # 查找所有匹配项
    matches = re.findall(pattern, markdown_text)
    # matches = [
    #     markdown_text
    # ]
    # logger.info(matches)
    # logger.info(f"Found {len(matches)} image URLs:")
    new_markdown = markdown_text
    
    for url in matches:
        # new_markdown += url
        # 调用 POST 接口获取新 image URL
        if(url.count('(')>url.count(')')):
            url = url + ')'
        imageUrl = "https:"+url
        # logger.info(f"imageUrl: {imageUrl}")
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json={"imageUrl": imageUrl}, headers=headers) as response:
                data = {}
                if response.status in (200, 201):
                    # 如果返回状态码是200或201，处理响应内容
                    data = await response.json()  # 假设服务器返回JSON格式数据
                    code = data.get("code", {})
                    # logger.info(f"Request response {data}")
                    if code == 200:
                        data = data.get("data", {})
                        new_url = data.get("location")
                        # 用新 URL 替换旧 URL
                        new_markdown = new_markdown.replace(url, new_url)
                        # logger.info(f"new_markdown: {new_markdown}")
                        return new_markdown
                    else:
                        logger.info(f"Request failed with status code: {data}")
                
    return new_markdown
async def process_discussion(province, paperId, question, explanation):

    # 解析题目
    try:
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(question, 'html.parser')

        # 获取试卷名称
        title = soup.find('h3', align='center').string
        logger.info(f"试卷名称: {title}")
        year, department = getTitleInfo(province, title)
        logger.info(f"试卷名称: {title}")
        questions = []
        material_points_tags = []
        introduction = ''
        if len(soup.find_all('h3')) == 3:
            index = 1
            # 获取说明
            introduction = soup.find_all('h3')[1].find_next_sibling(text=True).strip()
            # logger.info(f"说明: {introduction}")
            # 获取材料
            material = soup.find_all('h3')[2].find_next().get_text().strip()
            material_points_tags = soup.find_all('h3')[2].find_next_siblings(['p','b'])
            material_points = []
            for tag in material_points_tags:
                if tag.name == 'b' :
                    break
                if tag.get_text(strip=True).startswith(f"第1题"):
                    break
                text_content = tag.get_text(strip=True)
                material_points.append(text_content)
            material = '\n'.join(material_points)
            # logger.info(f"材料: {material}")

            # 获取各个试题
            question_start_tags = soup.find_all('b')
            for index, question_start_tag in enumerate(question_start_tags, start=1):
                # question_text = question.find_next_sibling('p').get_text().strip()
                question_tags = question_start_tag.find_next_siblings(['p'])
                question_texts = []
                for _, question in enumerate(question_tags):
                    question_text = question.get_text().strip()
                    question_texts.append(question_text)
                    # logger.info(f"{question_text}")
                    # 检查是否含有 img 标签
                    img_tag = question.find('img')
                    if img_tag:
                        # 获取 src
                        src = img_tag['src']
                        # 转换为 markdown 格式
                        image = f"![]({src})"
                        # logger.info(f"image: {image}")
                        question_texts.append(image)

                question_text = '\n'.join(question_texts)
                question_text = re.sub(r"^第\d+题：", "", question_text)                       
                # logger.info(f"{question_text}")
                # logger.info(f"第{i}题: {question_text}")
                question_title = f"{title} 第{index}题"
                questions.append({
                    'comment': paperId,
                    'year': year,
                    'province': province,
                    'departmentId': '0',
                    'department': department,
                    'title': question_title,
                    'origin': title,
                    'introduction': await replace_image_urls(introduction),
                    'material': await replace_image_urls(material),
                    'text': await replace_image_urls(question_text)
                })
        elif len(soup.find_all('h3')) == 1:
            # 获取说明
            # introduction = soup.find_all('h2')[0].find_next_sibling(text=True).strip()
            # 提取审题部分紧接着的p标签内容，根据需求调整选择器
            if len(soup.find_all('h2')) > 2:
                introduction_points_tags = soup.find_all('h2')[0].find_next_siblings(['p','h2'])
                introduction_points = []
                for tag in introduction_points_tags:
                    if tag.name == 'h2':
                        break
                    text_content = tag.get_text(strip=True)
                    introduction_points.append(text_content)
                introduction = '\n'.join(introduction_points)
                introduction = await replace_image_urls(introduction)
                # logger.info(f"说明: {introduction}")
                material_points_tags = soup.find_all('h2')[1].find_next_siblings(['p','h2'])
            else:
                if soup.find('div', id='printcontent'):
                    content_div = soup.find('div', id='printcontent').find('div')
                    material_points_tags = content_div.find_next('p').find_next_siblings(['p'])
                    
            # logger.info(f"material_points_tags: {material_points_tags}")

            # 提取材料
            material_list = []
            material_points = []
            next_tag_p = None
            for tag in material_points_tags:
                if tag.name == 'h2':
                    # 新的材料主题
                    if len(material_points) > 0:
                        material_content = '\n'.join(material_points)
                        material_content = await replace_image_urls(material_content)
                        material_list.append(material_content)
                        material_points = []
                    break
                # elif tag.find('b'):
                #     # 新的材料主题
                #     next_tag_p = tag
                #     if len(material_points) > 0:
                #         material_content = '\n'.join(material_points)
                #         material_content = await replace_image_urls(material_content)
                #         material_list.append(material_content)
                #         material_points = []
                #     break

                text_content = tag.get_text(strip=True)
                pattern = r'材料\d{1}'
                match = re.search(pattern, text_content)
                if match:
                    # 新的材料主题
                    if len(material_points) > 0:
                        material_content = '\n'.join(material_points)
                        material_content = await replace_image_urls(material_content)
                        material_list.append(material_content)
                        material_points = []
                material_points.append(text_content)
            
            # logger.info(f"material_list {material_list}")
            for index, material in enumerate(material_list):
                logger.info(f"材料: {index}")
            
            # 获取题目
            if len(soup.find_all('h2')) > 2:
                question_tags = soup.find_all('h2')[2].find_next_siblings(['p'])
            elif next_tag_p:
                    content_div = soup.find('div', id='printcontent').find('div').find()
                    question_tags = next_tag_p.find_next_siblings(['p'])
            
            logger.info(f"next_tag_p {next_tag_p}")

            question_text_list = []
            index = 1
            for _, question in enumerate(question_tags):
                question_text = question.get_text().strip()
                # 检查是否含有 img 标签
                img_tag = question.find('img')
                if img_tag:
                    # 获取 src
                    src = img_tag['src']
                    # 转换为 markdown 格式
                    image = f"![]({src})"
                    question_text = '\n'.join([question_text, image])

                if len(soup.find_all('h2')) > 2:
                    pattern = r'(\d+)分'
                    match = re.search(pattern, question_text)
                    if match:
                        # 这里是标题
                        # 先把前面的内容给集成进去
                        
                        if len(question_text_list)>0:
                            question_title = f"{title} 第{index}题"
                            
                            question_content = '\n'.join(question_text_list)
                            question_content = await replace_image_urls(question_content)
                            # question_content_list.append(question_content)
                            match = re.search(pattern, question_content)
                            fullScore = match.group(1)
                            logger.info(f"{title} 第{index}题 fullScore {fullScore}")
                            questions.append({
                                'comment': paperId,
                                'year': year,
                                'province': province,
                                'departmentId': '0',
                                'department': department,
                                'name': question_title,
                                'typeId': '1',
                                'origin': title,
                                'fullScore': fullScore,
                                'introduction': introduction,
                                'contents': material_list,
                                'text': question_content
                            })
                            question_text_list = []
                            index += 1
                    question_text_list.append(question_text)
                elif len(soup.find_all('b')) >= 2:
                    match = re.match(r'^第[一二三四五六七八九十]+题：$', question_text)
                    if match:
                        question_title = f"{title} 第{index}题"
                        if len(question_text_list)>0:
                            question_content = '\n'.join(question_text_list)
                            question_content = await replace_image_urls(question_content)
                            # question_content_list.append(question_content)
                            pattern = r'(\d+)分'
                            fullScore = 0
                            match = re.search(pattern, question_content)
                            if match:
                                fullScore = match.group(1)
                                logger.info(f"{title} 第{index}题 fullScore {fullScore}")
                            questions.append({
                                'comment': paperId,
                                'year': year,
                                'province': province,
                                'departmentId': '0',
                                'department': department,
                                'name': question_title,
                                'typeId': '1',
                                'origin': title,
                                'fullScore': fullScore,
                                'introduction': introduction,
                                'contents': material_list,
                                'text': question_content
                            })
                            question_text_list = []
                            index += 1
                    
                    question_text_list.append(question_text)
                    

            if len(question_text_list)>0:
                question_title = f"{title} 第{index}题"
                question_content = '\n'.join(question_text_list)
                question_content = await replace_image_urls(question_content)
                # question_content_list.append(question_content)
                fullScore = 0
                pattern = r'（(\d+)分）'
                match = re.search(pattern, question_content)
                if match:
                    fullScore = match.group(1)
                    logger.info(f"{title} 第{index}题 fullScore {fullScore}")
                questions.append({
                    'comment': paperId,
                    'year': year,
                    'province': province,
                    'departmentId': '0',
                    'department': department,
                    'name': question_title,
                    'typeId': '1',
                    'origin': title,
                    'fullScore': fullScore,
                    'introduction': introduction,
                    'contents': material_list,
                    'text': question_content
                })
        for idx, question in enumerate(questions):
            logger.info(f"题目 {idx + 1}: {question['name']}")

    except Exception as e:
            # Rollback on error to maintain consistency and log details for debugging
            # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # 解析答案解析
    analysis_points = []    
    try:
        logger.info("解析答案解析")
        
        # logger.info(f"{explanation}")
        # 从HTML文本创建一个BeautifulSoup对象，使用lxml作为解析器
        explanation = re.sub(r'<p=\s*align:\s*center\s*>', r'<p align="center">', explanation)
        soup = BeautifulSoup(explanation, 'html.parser')

        # 找到试卷名称
        exam_title_tag = soup.find('h3', align='center')
        exam_title = exam_title_tag.get_text(strip=True) if exam_title_tag else "无标题"

        logger.info(f"试卷名称: {exam_title}")

        # 初始化列表来存储题目信息
        explanations = []
        index = 1
        # 找到所有 <blockquote><p> ，标记每组 "参考答案" 的起始
        # answer_blocks = soup.find_all('blockquote')

        answer_blocks = exam_title_tag.find_all_next('blockquote')
        if len(answer_blocks) == 0:
            answer_blocks = exam_title_tag.find_all_next('div', class_='bs-callout')
            if len(answer_blocks) == 0 and soup.find('div', id='printcontent'):
                content_div = soup.find('div', id='printcontent').find('div')
                for title_p in content_div.find_all('p'):
                    if title_p.find('b'):
                        answer_blocks.append(title_p)

        logger.info(f"{answer_blocks}")
        if len(answer_blocks) == 0:
            raise HTTPException(status_code=500, detail="Answer block is empty")
        
        answers_list = []
        for block in answer_blocks:
            # 收集此 block 后面的<p>直到下一次 <blockquote> 或文档结尾
            next_sibling = block.find_next_sibling('p')
            answer_items = []
            
            while next_sibling and next_sibling.name == 'p':
                items_text = next_sibling.get_text(separator="\n").strip()
                # logger.info(items_text)
                answer_items.append(items_text)
                next_sibling = next_sibling.find_next_sibling('p')
            
            if len(answer_items)>0:
                answers_list.append('\n'.join(answer_items))

        # 显示结果
        for idx, answer in enumerate(answers_list):
            logger.info(f"参考答案 {idx + 1}:")
            explanations.append({
                # 'analysis': '\n'.join(analysis_points),
                # 'mindmapUrl': mind_map_image_url,
                'sampleAnswer': answer,
            })
            index += 1
        # return {"message": "Article processed and data updated successfully."}
    except Exception as e:
        # Rollback on error to maintain consistency and log details for debugging
        # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    # 将每个 questions 和 explanations 元素的字段合并到一个新的字典中，添加到 interview 列表中
    logger.info(f"questions length {len(questions)}")
    logger.info(f"explanations length {len(explanations)}")
    interviews = []
    if len(questions) != len(explanations):
        raise HTTPException(status_code=500, detail="questions length is not equal to explanations length")
    for q, e in zip(questions, explanations):
        merged_entry = {**q, **e}
        interviews.append(merged_entry)
    logger.info(f"interviews length {len(interviews)}")
    return interviews

async def fetch_html(url, referer: str = None):
    logger.info(url)
    timestamp = int(time.time())
    headers = {
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        # "Cookie": "connect.sid=s%3AFIZCYvlp4vhfk4l5eEq9rr74JCd2an67.uP2a3PFUS8LNC6LVfVaEu2XoG27NIIymPDducAD%2BM48; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1732881600; HMACCOUNT=1A150266D1AAAB30; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; province=%E5%9B%BD%E8%80%83; Hm_lpvt_db5c56a1da081947699f2e5bece459c7=1734586863",
        # "Cookie": f"connect.sid=s%3AasmGihKKO8OTgnFL2y_LgZmYVtts86x6.bbnOMAmmxvMpdGk7ctgHBdB7W4CTwE47z0Ku0x9e9xA; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734590397; HMACCOUNT=96C839E210B265AA; province=%E5%9B%BD%E8%80%83; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        # "Cookie": f"connect.sid=s%3Ae2VDDxSsjro9jpjIo6xX-b2ZgyS34FQN.GeKw6EjEaMKPbEBIJ3C1ldh5jRuoAcBvbTEqYUuYwN0; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734658177; HMACCOUNT=C3C8CCD265B20BCC; cls=%E7%94%B3%E8%AE%BA; province=%E5%9B%BD%E8%80%83; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        "Cookie": f"connect.sid=s%3Ae2VDDxSsjro9jpjIo6xX-b2ZgyS34FQN.GeKw6EjEaMKPbEBIJ3C1ldh5jRuoAcBvbTEqYUuYwN0; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734658177; HMACCOUNT=C3C8CCD265B20BCC; cls=%E7%94%B3%E8%AE%BA; province=%E6%B5%99%E6%B1%9F; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 QuarkPC/1.10.0.169"
    }
    if referer:
        headers['Referer'] = referer
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()

async def getPaperList(url):
    html_content = await fetch_html(url)
    # 使用BeautifulSoup解析HTML内容
    soup = BeautifulSoup(html_content, 'lxml')

    # 找到ID为paperlist的表格
    table = soup.find('table', {'id': 'paperlist'})

    # 初始化结果列表
    papers = []

    # 在指定表格中查找所有符合条件的链接标签<a>，并提取其中的数字部分
    for link in table.find_all('a', href=True):
        # 检查链接是否以/paper/开头以确保匹配设计要求
        if link['href'].startswith('/paper/'):
            # 提取所有以/paper/开头的链接中的数字部分
            number = link['href'].split('/')[-1]
            papers.append(number)

    logger.info(papers)  # 输出结果 ['1727924080287', '1727924080186']
    return papers
async def scrape(province, listUrl, paperId):
    
    paperUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    paper_content = await fetch_html(paperUrl, listUrl)

    explanUrl = f"https://www.gkzenti.cn/explain/{paperId}"

    explan_content = await fetch_html(explanUrl)
    
    explanWithCodeUrl = await getDecodedUrls(paperId)

    logger.info(f"{explanUrl}, {explanWithCodeUrl}")
    if(explanUrl == None or explanWithCodeUrl == None):
        raise Exception("Failed to fetch paper urls")
    
    explan_content = await fetch_html(explanWithCodeUrl, explanUrl)
    discussions = await process_discussion(province, paperId, paper_content, explan_content)
    if not discussions:
        raise Exception("Failed to process discussion")
    
    discussion_collection=await get_discussion_collection()
    for discussion in discussions:
        logger.info(discussion["name"])
        new_discussion = await discussion_collection.insert_one(discussion)
        created_interview = await discussion_collection.find_one({"_id": new_discussion.inserted_id})
        # logger.info(f"Created interview: {created_interview}")

def save_paper_id(url, paper_id):

    path = url.split('?')[-1]
    path = unquote(path)
    path = path.replace('cls=', '')
    path = path.replace('=', '')
    path = path.replace('&', '')

    fileName = os.path.join("discussion_papers", path + ".txt")
    
    with open(fileName, "a") as file:
        file.write(f"{paper_id}\n")
def load_successful_paper_ids(url):
    path = url.split('?')[-1]
    path = unquote(path)
    path = path.replace('cls=', '')
    path = path.replace('=', '')
    path = path.replace('&', '')
    fileName = os.path.join("discussion_papers", path + ".txt")
    try:
        with open(fileName) as file:
            return set(file.read().splitlines())
    except FileNotFoundError:
        return set()        
def generate_pageurls(n):
    #base_url = "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%9B%BD%E8%80%83&index="
    # base_url = "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E6%B5%99%E6%B1%9F&index="
    
    # 使用列表推导式生成URL列表
    # urls = [f"{base_url}{i}" for i in reversed(range(1, n + 1))]


    urls = [
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=国考&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=浙江&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=山东&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=江苏&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=广东&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=四川&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=福建&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=广西&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=安徽&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=上海&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=北京&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=辽宁&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=天津&index=1", # 天津
    ]

    urls = [
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=河北&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=海南&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=河南&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=江西&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=湖南&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=湖北&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=山西&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=内蒙古&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=吉林&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=黑龙江&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=贵州&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=重庆&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=陕西&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=甘肃&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=云南&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=新疆&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=宁夏&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=青海&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=深圳&index=1",
        "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=广州&index=1",
    ]

    return urls

async def periodic_scraping_task():
    try:
        os.makedirs('discussion_papers', exist_ok=True)
        # logger.info(f"Directory '{path}' is created or already exists.")
    except Exception as e:
        logger.info(f"An error occurred while creating the directory: {e}")

    url_list = generate_pageurls(1)
    for url in url_list:
        # url = "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=%E6%B5%99%E6%B1%9F&index=1"
        # url = "https://www.gkzenti.cn/paper?cls=%E7%94%B3%E8%AE%BA&province=%E5%9B%BD%E8%80%83&index=1"
        logger.info(url)
        pattern = r'province=([^&]*)'
        # 使用 re.search() 在 URL 中查找模式
        match = re.search(pattern, url)
        province = '国家'
        if match:
            province = match.group(1)  # 提取第一个捕获组，即 province 的值
            if province == "国考":
                province = "国家"
        logger.info(f"Province: {province}")
        paperIds = await getPaperList(url)
        logger.info(paperIds)
        successful_ids = load_successful_paper_ids(url)
        for paperId in paperIds:
            if paperId not in successful_ids:
                # paperId = '1551781245901o2n'
                # paperId = '1627554027915'
                # paperId = '1647786976704'
                # paperId = '1661056209087'
                try:
                    logger.info(f"Scraping paper with ID: {paperId}")
                    await scrape(province, url, paperId)
                    save_paper_id(url, paperId)
                except Exception as e:
                    logger.info(f"Error occurred while scraping paper with ID {paperId}: {e}")
                rand = random.randint(1, 20)
                # break
                await asyncio.sleep(50 + rand)  # 每秒钟运行一次任务
        # break


async def fetch_from_external_service(record_id):
    url = f"https://mian.xiaohe.biz/api/sys/discussions/checkTypes/{record_id}"
    headers = {
        # 'Authentication': f'{authToken}',  # 确保替换为你的真实认证令牌
        'Content-Type': 'application/json'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            return await response.json()

async def process_discussion_types():
    collection = await get_discussion_collection()
    
    cursor = collection.find({})
    discussions = await cursor.to_list(length=None)
    
    for discussion in discussions:
        record_id = discussion.get("_id")
        if record_id:
            result = await fetch_from_external_service(record_id)
            print(result)  # 或者根据需要进行进一步的操作