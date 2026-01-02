# tasks.py

import re
import aiohttp
import asyncio
import random
import os
from bs4 import BeautifulSoup
from urllib.parse import unquote
from app.logs import get_logger
from fastapi import FastAPI, HTTPException, Depends
from models.user import User  # 从models导入用户模型
from app.database import get_question_collection  # 从app导入数据库函数
from app.tasks_lib import fetch_html, getPaperList, fetch_captcha_svg, image2Code, getUrls
from app.tasks_lib import getTitleInfo, replace_image_urls,save_paper_id,load_successful_paper_ids
from app.tasks_lib import setup_logger

# 为当前模块创建专用logger
logger = setup_logger(__name__)

# 获取保存目录
save_directory = 'papers'


def get_pageurls():
    urls = [
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=国家",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=联考",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=浙江",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=山东",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=江苏",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=广东",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=四川",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=福建",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=广西",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=安徽",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=上海",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=北京",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=辽宁",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=天津",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=河北",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=海南",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=河南",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=江西",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=湖南",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=湖北",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=山西",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=内蒙古",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=吉林",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=黑龙江",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=贵州",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=重庆",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=陕西",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=甘肃",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=新疆",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=青海",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=深圳",
        "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=其他",
    ]

    return urls

async def process_question(province, paperId, question, explanation):

    # 解析题目
    try:
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(question, 'html.parser')

        # 获取试卷名称
        title_tag = soup.find('h3', align='center')
        title = title_tag.string if title_tag else "无标题"
        logger.info(f"试卷名称: {title}")
        year, department, title = getTitleInfo(title)
        logger.info(f"试卷名称: {title}")
        questions = []

        if soup.find('div', class_='subtitle'):
            logger.info("Detected new HTML structure with div.subtitle")
            current_typeName = ""
            current_material = ""

            rows = soup.find_all('div', class_='row')
            for row in rows:
                # 1. 获取子标题subtitle，并提取类别名称typeName
                subtitle_div = row.find('div', class_='subtitle')
                if subtitle_div:
                    subtitle_text = subtitle_div.get_text(strip=True)
                    match = re.search(r'[一二三四五六七八九十]+、(.*?)(?:。|$)', subtitle_text)
                    if match:
                        current_typeName = match.group(1)
                    else:
                        current_typeName = subtitle_text
                    current_material = "" # 切换题型时清空材料
                    logger.info(f"Category: {current_typeName}")
                    continue

                # 2. 处理资料分析的子标题sub2title和材料
                sub2title_div = row.find('div', class_='sub2title')
                if sub2title_div:
                    cols = row.find_all('div', class_='col-xs-12')
                    material_parts = []
                    for col in cols:
                        if 'sub2title' in col.get('class', []):
                            continue
                        for child in col.children:
                            if child.name == 'p':
                                p_text = child.get_text(strip=True)
                                img = child.find('img')
                                if img:
                                    src = img.get('src')
                                    p_text += f" ![]({src})"
                                material_parts.append(p_text)
                            elif child.name == 'img':
                                src = child.get('src')
                                material_parts.append(f"![]({src})")
                            elif isinstance(child, str) and child.strip():
                                material_parts.append(child.strip())
                    current_material = "\n".join(material_parts)
                    continue

                # 3. 获取题目内容text，以及题目选项A,B,C,D
                left_div = row.find('div', class_='left')
                right_div = row.find('div', class_='right')
                if left_div and right_div:
                    index = left_div.get_text(strip=True)
                    question_texts = []
                    options_dict = {}

                    for child in right_div.children:
                        if child.name == 'p':
                            p_text = child.get_text(strip=True)
                            imgs = child.find_all('img')
                            for img in imgs:
                                src = img.get('src')
                                p_text += f" ![]({src})"
                            if p_text:
                                question_texts.append(p_text)
                        elif child.name == 'div':
                            classes = child.get('class', [])
                            if any(c.startswith('col-xs-') for c in classes):
                                opt_text = child.get_text(strip=True)
                                imgs = child.find_all('img')
                                for img in imgs:
                                    src = img.get('src')
                                    opt_text += f" ![]({src})"
                                match = re.match(r'^([A-D])、(.*)', opt_text, re.DOTALL)
                                if match:
                                    options_dict[match.group(1)] = match.group(2).strip()

                    question_text = "\n".join(question_texts)
                    question_title = f"{title} 第{index}题"
                    
                    questions.append({
                        'comment': paperId,
                        'year': year,
                        'careerId': '2',
                        'careerName': '事业单位',
                        'province': province,
                        'departmentId': '0',
                        'department': department,
                        'title': question_title,
                        'origin': title,
                        'index': index,
                        'material': await replace_image_urls(current_material),
                        'text': await replace_image_urls(question_text),
                        'typeName': current_typeName,
                        'options': options_dict
                    })
        
    except Exception as e:
            # Rollback on error to maintain consistency and log details for debugging
            # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # 解析答案解析
    explanations = []
    try:
        logger.info("解析答案解析")
        
        logger.info(f"{explanation}")
        # 从HTML文本创建一个BeautifulSoup对象，使用lxml作为解析器
        soup = BeautifulSoup(explanation, 'html.parser')

        # 找到试卷名称
        exam_title_tag = soup.find('h3', align='center')
        exam_title = exam_title_tag.get_text(strip=True) if exam_title_tag else "无标题"

        logger.info(f"试卷名称: {exam_title}")

        if soup.find('div', class_='row') and soup.find('div', class_='right'):
            logger.info("Detected new Explanation HTML structure with div.row")
            rows = soup.find_all('div', class_='row')
            for row in rows:
                left = row.find('div', class_='left')
                right = row.find('div', class_='right')
                if left and right:
                    explanation_texts = []
                    correct_answer = ""
                    
                    for child in right.children:
                        if child.name == 'p':
                            text = child.get_text(strip=True)
                            imgs = child.find_all('img')
                            for img in imgs:
                                src = img.get('src')
                                text += f" ![]({src})"
                            
                            if text:
                                explanation_texts.append(text)
                            
                            match = re.search(r'故正确答案为[：:]?([A-D]+)', text)
                            if match:
                                correct_answer = match.group(1)
                        elif child.name == 'img':
                             src = child.get('src')
                             explanation_texts.append(f"![]({src})")
                        elif isinstance(child, str) and child.strip():
                             explanation_texts.append(child.strip())
                    
                    full_explanation = "\n".join(explanation_texts)
                    
                    explanations.append({
                        'explanation': await replace_image_urls(full_explanation),
                        'correctAnswer': correct_answer,
                        'allowMultipleSelections': len(correct_answer) > 1 if correct_answer else False
                    })
        else:
            # 初始化列表来存储题目信息
            index = 1
            for question_block in soup.find_all('blockquote'):
                # 提取题目的标题 （解析与参考答案）
                # question_title_tag = question_block.find_previous('p', string=lambda x: x and "题" in x)
                # question_title = question_title_tag.get_text(strip=True) if question_title_tag else "无题目文字"

                # 提取审题部分紧接着的p标签内容，根据需求调整选择器
                analysis_points_tags = question_block.find_next_siblings(['p','b', 'br'])

                analysis_points = []
                for tag in analysis_points_tags:
                    text_content = tag.get_text(strip=True)
                    # logger.info(f"text_content")
                    if text_content.startswith("思维导图") or any(x in text_content for x in ["参考答案"]) :
                        break
                    else:
                        analysis_points.append(text_content)

                # 提取思维导图，通常它在<b> 思维导图 </b>后面，与图片对应，假设以img src表示。
                mind_map_tag = question_block.find_next('b', string="思维导图")
                mind_map_image_url = None

                if mind_map_tag:
                    img_tag = mind_map_tag.find_next('img')
                    mind_map_image_url = img_tag['src'] if img_tag else ""
                    mind_map_image_url = await replace_image_urls(mind_map_image_url)
                    logger.info(mind_map_image_url)
                # 提取参考答案，在<b> 参考答案 </b>或<b> 参考解析 </b>等类似标记后采集相关内容。
                reference_answer_starting_point = question_block.find_next('b', string=lambda text: text and ("参考答案" in text or "参考解析" in text))
                # reference_answer_starters = question_block.find_all('b', string="参考答案")

                reference_answers = []
                if reference_answer_starting_point:
                    # ref_answer_tags = reference_answer_starting_point.find_all_next(string=lambda t: t.name == 'p')
                    # 在每个<b>标签后找到下一个同级标题或换行分隔
                    next_b_tag = reference_answer_starting_point.find_next('b', string=lambda text: text and "题解析与参考答案" in text)
                    logger.info(next_b_tag)
                    logger.info("--------")
                    ref_answer_tags = reference_answer_starting_point.find_all_next(['p', 'b'])
                    ref_ans_txt = ""
                    for tag in ref_answer_tags:
                        if tag == next_b_tag:
                            logger.info("----- stop ----- ")
                            break  # 遇到了下一个问题标题，停止
                        if tag.name == 'p' and tag.get_text(strip=True).startswith("&nbsp"):
                            logger.info("----- stop2 ----- ")
                            break  # 遇到了下一个问题标题，停止

                        if tag.name == 'p' and tag.parent.name != "blockquote":
                            ref_ans_txt=tag.get_text(strip=True)
                            # logger.info(ref_ans_txt)
                            reference_answers.append(ref_ans_txt)
                        if tag.name == 'footer':
                            logger.info("----- footer stop ----- ")
                            break  # 遇到了下一个问题标题，停止
                        #if not tag.find_previous('b', string=lambda x: x and "第" in x and "题解析与参考答案" in x):
                        #    reference_answers.append(tag.get_text(strip=True))
                        # else:
                        #    break
                        # if "第" not in ref_ans_txt:  # 在没有找到下一个问题指针前收集所有标准答案P块内容。
                        #    reference_answers.append(tag.get_text(strip=True))
                        # else:
                        #    break

                    #reference_answers.append(ref_ans_txt)
                
                explanations.append({
                    'analysis': '\n'.join(analysis_points),
                    # 'mindmapUrl': mind_map_image_url,
                    'sampleAnswer': '\n'.join(reference_answers).split("\n\n\n欢迎使用公开真题库")[0], #  移除"\n\n\n欢迎使用公开真题库" 以及后面的内容
                })
                index += 1
        # return {"message": "Article processed and data updated successfully."}
    except Exception as e:
        # Rollback on error to maintain consistency and log details for debugging
        # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    # 将每个 questions 和 explanations 元素的字段合并到一个新的字典中，添加到 interview 列表中
    interviews = []
    logger.info(f"Questions: {len(questions)}, Explanations: {len(explanations)}")
    
    count = min(len(questions), len(explanations))
    for i in range(count):
        merged_entry = {**questions[i], **explanations[i]}
    logger.info(interviews)
    return interviews


async def scrape_process(listUrl, paperId, province):
    question_collection=await get_question_collection()
    questionUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    question_content = await fetch_html(questionUrl, listUrl)
    await asyncio.sleep(5)  # 每秒钟运行一次任务
    questionUrl, explanUrl = await getUrls(paperId)
    logger.info(f"{questionUrl}, {explanUrl}")
    if(questionUrl == None or explanUrl == None):
        raise Exception("Failed to fetch paper urls")
    await asyncio.sleep(5)  
    explan_content = await fetch_html(explanUrl, questionUrl)
    questions = await process_question(province, paperId, question_content, explan_content)
    if not questions:
        raise Exception("Failed to process questions")
    for question in questions:
        logger.info(question["title"])
        new_question = await question_collection.insert_one(question)
        created_question = await question_collection.find_one({"_id": new_question.inserted_id})
        # logger.info(f"Created question: {created_question}")


async def periodic_scraping_questitask():
    try:
        os.makedirs(save_directory, exist_ok=True)
        # logger.info(f"Directory '{path}' is created or already exists.")
    except Exception as e:
        logger.info(f"An error occurred while creating the directory: {e}")

    url_list = get_pageurls()
    for url in url_list:
        logger.info(url)
    
        # 提取URL中的省份信息
        # 例如: "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=贵州" → "贵州"
        # 例如: "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=浙江&index=2" → "浙江"
        province = url.split("province=")[-1].split("&")[0] if "province=" in url else "未知省份"
        # URL解码省份名称
        province = unquote(province)
        logger.info(f"正在处理省份: {province}")
        
        paperIds = await getPaperList(url)
        logger.info(paperIds)
        successful_ids = load_successful_paper_ids(url, save_directory)
        for paperId in paperIds:
            if paperId not in successful_ids:
                # paperId = '1668003216766'
                # paperId = '1702961776894'
                # paperId = '1667998867772'
                max_retries = 3
                success = False
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Scraping paper with ID: {paperId} (attempt {attempt + 1}/{max_retries})")
                        await scrape_process(url, paperId, province)
                        save_paper_id(url, paperId, save_directory)
                        success = True
                        break
                    except Exception as e:
                        last_error = e
                        logger.info(f"Attempt {attempt + 1} failed for paper ID {paperId}: {e}")
                        if attempt < max_retries - 1:  # 不是最后一次尝试
                            await asyncio.sleep(5)  # 重试前等待5秒
                
                if not success:
                    logger.info(f"Failed to scrape paper ID {paperId} after {max_retries} attempts. Last error: {last_error}")
                
                rand = random.randint(1, 10)
                await asyncio.sleep(30 + rand)  # 每秒钟运行一次任务
                # break
        # break

