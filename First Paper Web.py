import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from urllib.parse import urljoin

# 设置请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 基础URL
base_url = "https://www.shijuan1.com"


def get_paper_list(page_url):
    """爬取列表页，获取所有试卷的详情页链接"""
    print(f"正在爬取列表页: {page_url}")

    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        papers = []
        table = soup.find('table')
        if not table:
            print("没找到表格")
            return papers

        rows = table.find_all('tr')[1:]  # 跳过表头

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 1:
                title_tag = cols[0].find('a', class_='title')
                if title_tag:
                    title = title_tag.text.strip()
                    detail_link = title_tag['href']
                    full_detail_link = urljoin(base_url, detail_link)

                    # 其他信息（可选）
                    file_type = cols[1].text.strip() if len(cols) > 1 else ''
                    date = cols[5].text.strip() if len(cols) > 5 else ''

                    papers.append({
                        '标题': title,
                        '详情页链接': full_detail_link,
                        '文件类型': file_type,
                        '上传日期': date
                    })

        print(f"本页找到 {len(papers)} 份试卷")
        return papers

    except Exception as e:
        print(f"列表页爬取出错: {e}")
        return []


def get_download_link(detail_url):
    """访问详情页，提取下载链接"""
    try:
        response = requests.get(detail_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 找到下载链接所在的ul
        download_ul = soup.find('ul', class_='downurllist')
        if download_ul:
            a_tag = download_ul.find('a')
            if a_tag and a_tag.get('href'):
                download_path = a_tag['href']
                full_download_url = urljoin(base_url, download_path)
                return full_download_url

        return None

    except Exception as e:
        print(f"详情页爬取出错 {detail_url}: {e}")
        return None


def download_file(url, save_path):
    """下载文件"""
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"下载失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"下载出错: {e}")
        return False


def get_total_pages(first_page_url):
    """获取总页数"""
    try:
        response = requests.get(first_page_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        page_info = soup.find('span', class_='pageinfo')
        if page_info:
            import re
            match = re.search(r'共\s*(\d+)\s*页', page_info.text)
            if match:
                return int(match.group(1))

        # 从分页链接推断
        pagelist = soup.find('ul', class_='pagelist')
        if pagelist:
            links = pagelist.find_all('a')
            max_page = 1
            for link in links:
                href = link.get('href', '')
                match = re.search(r'list_728_(\d+)\.html', href)
                if match:
                    page_num = int(match.group(1))
                    max_page = max(max_page, page_num)
            return max_page

        return 1

    except Exception as e:
        print(f"获取页数出错: {e}")
        return 1


def main():
    # 创建保存文件夹
    import os
    if not os.path.exists('downloaded_papers'):
        os.makedirs('downloaded_papers')

    # 第一步：爬取所有试卷的详情页链接
    list_page_url = "https://www.shijuan1.com/a/sjsxgk/"

    print("正在获取总页数...")
    total_pages = get_total_pages(list_page_url)
    print(f"总页数: {total_pages}")

    all_papers = []

    # 遍历所有列表页
    for page in range(1, total_pages + 1):
        if page == 1:
            page_url = list_page_url
        else:
            page_url = f"https://www.shijuan1.com/a/sjsxgk/list_728_{page}.html"

        papers = get_paper_list(page_url)
        all_papers.extend(papers)

        # 每爬一页保存一次进度
        df_temp = pd.DataFrame(all_papers)
        df_temp.to_csv('papers_list.csv', index=False, encoding='utf-8-sig')

        time.sleep(2)  # 礼貌性停顿

    print(f"\n共找到 {len(all_papers)} 份试卷")

    # 第二步：遍历每个详情页，获取下载链接并下载
    results = []

    for i, paper in enumerate(all_papers):
        print(f"\n[{i + 1}/{len(all_papers)}] 处理: {paper['标题']}")

        # 获取下载链接
        download_url = get_download_link(paper['详情页链接'])

        if download_url:
            print(f"  找到下载链接: {download_url}")

            # 生成文件名（用标题，但去掉非法字符）
            filename = paper['标题'].replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace(
                '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')

            # 从下载链接中获取文件扩展名
            import os.path
            ext = os.path.splitext(download_url)[1]
            if not ext:
                ext = '.rar'  # 默认扩展名

            save_path = os.path.join('downloaded_papers', f"{filename}{ext}")

            # 下载文件
            if download_file(download_url, save_path):
                print(f"  下载成功: {save_path}")
                paper['下载状态'] = '成功'
                paper['本地文件'] = save_path
            else:
                print(f"  下载失败")
                paper['下载状态'] = '失败'
        else:
            print(f"  未找到下载链接")
            paper['下载状态'] = '无链接'

        paper['下载链接'] = download_url
        results.append(paper)

        # 每处理一个试卷停一下，防止被封
        time.sleep(1)

        # 每10个保存一次进度
        if (i + 1) % 10 == 0:
            df_progress = pd.DataFrame(results)
            df_progress.to_csv('download_progress.csv', index=False, encoding='utf-8-sig')

    # 保存最终结果
    df_final = pd.DataFrame(results)
    df_final.to_csv('download_complete.csv', index=False, encoding='utf-8-sig')

    # 统计
    success = len([r for r in results if r['下载状态'] == '成功'])
    failed = len([r for r in results if r['下载状态'] == '失败'])
    no_link = len([r for r in results if r['下载状态'] == '无链接'])

    print(f"\n========== 完成 ==========")
    print(f"总数: {len(results)}")
    print(f"下载成功: {success}")
    print(f"下载失败: {failed}")
    print(f"无下载链接: {no_link}")
    print(f"文件保存在: downloaded_papers/ 文件夹")


if __name__ == '__main__':
    main()