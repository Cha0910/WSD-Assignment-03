import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time


def crawl_saramin(pages=1):
    """
    사람인 채용공고를 크롤링하는 함수

    Args:
        pages (int): 크롤링할 페이지 수

    Returns:
        DataFrame: 채용공고 정보가 담긴 데이터프레임
    """

    jobs = []
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Whale/3.28.266.14 Safari/537.36'
    }

    for page in range(1, pages + 1):
        url = f"https://www.saramin.co.kr/zf_user/search?search_area=main&search_done=y&search_optional_item=n&loc_mcd=101000%2C102000&cat_mcls=2&recruitPage={page}&recruitSort=relation&recruitPageCount=40&inner_com_type=&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10&searchword=&show_applied=&quick_apply=&except_read=&ai_head_hunting=&mainSearch=n"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 채용공고 목록 가져오기
            job_listings = soup.select('div.item_recruit')

            for job in job_listings:
                try:
                    title_tag = job.select_one('h2.job_tit a')
                    title = title_tag.text.strip() if title_tag else '정보 없음'
                    job_link = 'https://www.saramin.co.kr' + title_tag['href'] if title_tag else '정보 없음'

                    # 회사명 및 링크
                    company_tag = job.select_one('strong.corp_name a')
                    company = company_tag.text.strip() if company_tag else '정보 없음'
                    company_link = 'https://www.saramin.co.kr' + company_tag['href'] if company_tag else '정보 없음'

                    # 채용 조건
                    conditions = job.select('div.job_condition span')
                    location = conditions[0].text.strip() if len(conditions) > 0 else '정보 없음'
                    career = conditions[1].text.strip() if len(conditions) > 1 else '정보 없음'
                    education = conditions[2].text.strip() if len(conditions) > 2 else '정보 없음'
                    employment_type = conditions[3].text.strip() if len(conditions) > 3 else '정보 없음'
                    salary = conditions[4].text.strip() if len(conditions) > 4 else '정보 없음'

                    # 직무 분야
                    sectors = job.select('div.job_sector a')
                    sector_list = [sector.text.strip() for sector in sectors]
                    job_sector = ', '.join(sector_list) if sector_list else '정보 없음'

                    # 등록일
                    register_date_tag = job.select_one('span.job_day')
                    register_date = register_date_tag.text.strip()
                    if '등록일' in register_date or '수정일' in register_date:
                        register_date = register_date.replace('등록일 ', '').replace('수정일 ', '')
                        register_date = f"20{register_date}"

                    else:
                        register_date = '정보 없음'

                    # 마감일
                    deadline_tag = job.select_one('span.date')
                    deadline = deadline_tag.text.strip()
                    if '내일마감' in deadline:
                        deadline = (datetime.now() + timedelta(days=1)).strftime('%Y/%m/%d')
                    elif '오늘마감' in deadline:
                        deadline = datetime.now().strftime('%Y/%m/%d')
                    elif '상시채용' in deadline:
                        deadline = '상시채용'
                    elif '채용시' in deadline:
                        deadline = '채용시'
                    else:
                        # "~ MM/DD(요일)" 형태를 "YYYY/MM/DD"로 변환
                        try:
                            deadline = deadline.replace('~ ', '').split('(')[0].strip()
                            deadline = datetime.strptime(deadline, '%m/%d').replace(
                                year=datetime.now().year).strftime('%Y/%m/%d')
                        except ValueError:
                            deadline = '정보 없음'

                    # 데이터 저장
                    jobs.append({
                        '채용 제목': title,
                        '채용 링크': job_link,
                        '회사명': company,
                        '회사 링크': company_link,
                        '지역': location,
                        '경력': career,
                        '학력': education,
                        '고용형태': employment_type,
                        '연봉': salary,
                        '직무 분야': job_sector,
                        '등록일': register_date,
                        '마감일': deadline,
                    })

                except AttributeError as e:
                    print(f"항목 파싱 중 에러 발생: {e}")
                    continue

            print(f"{page}페이지 크롤링 완료")
            time.sleep(3)  # 서버 부하 방지를 위한 딜레이

        except requests.RequestException as e:
            print(f"페이지 요청 중 에러 발생: {e}")
            continue

    return pd.DataFrame(jobs)

def main():
    # 서울, 경기 지역 it 개발 . 데이터 전체 크롤링
    df = crawl_saramin(pages=25) # 40 * 25 = 1000개 데이터
    df.to_csv('./data/saramin.csv', index=False)
    print(f"크롤링 완료: 총 {len(df)}개 공고 저장")

# 사용 예시
if __name__ == "__main__":
   main()