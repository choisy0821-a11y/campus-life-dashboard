import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import re

# 1. 화면 제목
st.title("🎓 캠퍼스 생활 설문조사 분석 웹앱")
st.write("인문사회대 학생들의 생활 습관, 만족도 및 한줄의견을 분석합니다.")

# 2. CSV 파일 업로드
uploaded_file = st.file_uploader("설문조사 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is not None:
    # CSV 파일 읽기
    df = pd.read_csv(uploaded_file)

    # -------------------------------------------------------------
    # 수치형 컬럼 강제 숫자 변환 (문자형 데이터 에러 방지)
    # -------------------------------------------------------------
    check_cols = ['공부시간', '수면시간', '스마트폰', '스마트폰 사용시간', '스마트폰시간', '만족도', '학교 생활 만족도']
    for col in check_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. 데이터 미리보기
    st.subheader("1. 데이터 미리보기")
    st.write(f"총 {len(df)}명의 응답 데이터가 있습니다.")
    st.dataframe(df.head())

    # 4. 결측치(빠진 값) 및 이상치 확인 (전처리 결과)
    st.subheader("2. 데이터 결측치 및 이상치 확인")

    # 각 컬럼별 비어있는(NaN) 값의 개수 계산
    missing_data = df.isnull().sum()
    missing_df = pd.DataFrame({"컬럼명": missing_data.index, "결측치 개수": missing_data.values})
    st.write("📌 빠진 값(결측치) 현황:")
    st.dataframe(missing_df)

    # 음수 시간 등 잘못된 입력값 점검 (0보다 작은 수치 확인)
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    invalid_rows = df[(df[numeric_cols] < 0).any(axis=1)]
    if not invalid_rows.empty:
        st.warning(f"⚠️ 0보다 작은 비정상적인 수치가 포함된 데이터가 {len(invalid_rows)}건 발견되었습니다.")
        st.dataframe(invalid_rows)
    else:
        st.success("✅ 음수 값과 같은 비정상 수치가 없습니다.")

    # 5. 학과 선택
    st.subheader("3. 학과별 데이터 필터링")

    # 학과 컬럼 존재 여부 확인 후 필터링
    if '학과' in df.columns:
        departments = ["전체"] + list(df['학과'].dropna().unique())
        selected_dept = st.selectbox("조회할 학과를 선택하세요:", departments)

        if selected_dept != "전체":
            filtered_df = df[df['학과'] == selected_dept]
        else:
            filtered_df = df
    else:
        st.info("'학과' 컬럼이 없어 전체 데이터를 표시합니다.")
        filtered_df = df

    # 6. 시각화 그래프 (생활 습관 및 만족도)
    st.subheader("4. 생활 습관 및 만족도 그래프")

    # 스마트폰 관련 컬럼명 탐색
    phone_col = None
    for name in ['스마트폰', '스마트폰 사용시간', '스마트폰시간']:
        if name in df.columns:
            phone_col = name
            break

    # 학과별 비교에 사용할 생활 습관 컬럼 목록
    habit_cols = [col for col in ['공부시간', '수면시간', phone_col] if col and col in df.columns]

    # (1) 학과별 생활 습관 비교 막대 그래프
    st.write("📊 **학과별 평균 생활 습관 비교**")
    if '학과' in df.columns and habit_cols:
        dept_avg = df.groupby('학과')[habit_cols].mean().reset_index()
        fig_habits = px.bar(
            dept_avg,
            x='학과',
            y=habit_cols,
            barmode='group',
            title="학과별 평균 시간 (시간 단위)"
        )
        st.plotly_chart(fig_habits, use_container_width=True)
    else:
        st.info("비교할 생활 습관 또는 학과 데이터가 부족합니다.")

    # (2) 생활 습관과 학교생활 만족도 간의 관계 (공부시간, 수면시간, 스마트폰)
    st.write("🔍 **생활 습관과 학교생활 만족도 간의 관계**")

    sat_col = None
    for name in ['학교 생활 만족도', '만족도']:
        if name in filtered_df.columns:
            sat_col = name
            break

    if sat_col:
        habits_to_plot = [
            ("공부시간", "공부시간" if "공부시간" in filtered_df.columns else None),
            ("수면시간", "수면시간" if "수면시간" in filtered_df.columns else None),
            ("스마트폰 사용시간", phone_col)
        ]

        cols = st.columns(3)

        for idx, (label, col_name) in enumerate(habits_to_plot):
            with cols[idx]:
                if col_name and col_name in filtered_df.columns:
                    clean_df = filtered_df.dropna(subset=[col_name, sat_col])
                    if len(clean_df) > 0:
                        fig = px.scatter(
                            clean_df,
                            x=col_name,
                            y=sat_col,
                            color='학과' if '학과' in clean_df.columns else None,
                            title=f"{label}({col_name}) vs {sat_col}",
                            trendline="ols"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"'{label}'에 유효한 데이터가 없습니다.")
                else:
                    st.warning(f"'{label}' 컬럼을 찾을 수 없습니다.")
    else:
        st.info("CSV 파일에 '만족도' 또는 '학교 생활 만족도' 컬럼이 필요합니다.")

    # 7. 학생들의 한줄의견 분석
    st.subheader("5. 💬 학생 한줄의견 분석")

    # 한줄의견 컬럼명 확인 ('한줄의견' 또는 '의견')
    opinion_col = None
    for col in ['한줄의견', '의견', '한줄 의견']:
        if col in filtered_df.columns:
            opinion_col = col
            break

    if opinion_col:
        # 비어있지 않은 텍스트만 추출
        opinions = filtered_df[opinion_col].dropna().astype(str).tolist()

        if len(opinions) > 0:
            # 1) 전체 텍스트 합치기 및 특수문자 제거 후 2글자 이상 단어 추출
            all_words = []
            for text in opinions:
                # 한글/영어/숫자만 남기고 공백 단위로 분리
                cleaned_text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text)
                words = cleaned_text.split()
                # 1글자 조사/단어(은, 는, 이, 가 등) 제외하고 2글자 이상만 수집
                meaningful_words = [w for w in words if len(w) >= 2]
                all_words.extend(meaningful_words)

            # 빈도수 상위 10개 단어 추출
            word_counts = Counter(all_words)
            top10 = word_counts.most_common(10)

            # 상위 10개 단어 막대 그래프
            st.write("📊 **가장 많이 등장한 단어 Top 10**")
            if top10:
                top10_df = pd.DataFrame(top10, columns=['단어', '빈도수'])
                fig_top10 = px.bar(
                    top10_df,
                    x='단어',
                    y='빈도수',
                    title=f"자주 등장하는 단어 상위 10개 ({selected_dept if '학과' in df.columns else '전체'})",
                    text='빈도수'
                )
                st.plotly_chart(fig_top10, use_container_width=True)
            else:
                st.write("분석할 단어가 충분하지 않습니다.")

            # 2) 긍정 / 부정 단어 사전 정의
            pos_dict = ['좋다', '좋음', '만족', '행복', '즐겁다', '재미', '보람', '추천', '편하다', '유익', '최고', '응원', '알참', '도움']
            neg_dict = ['힘들다', '아쉽다', '불만', '부족', '어렵다', '피곤', '싫다', '스트레스', '최악', '불편', '짜증', '노잼', '낙후']

            # 긍정 / 부정 단어 카운트 및 등장 목록 수집
            pos_found = []
            neg_found = []

            for word in all_words:
                for p in pos_dict:
                    if p in word:
                        pos_found.append(word)
                        break
                for n in neg_dict:
                    if n in word:
                        neg_found.append(word)
                        break

            pos_count = len(pos_found)
            neg_count = len(neg_found)

            st.write("⚖️ **긍정 및 부정 감성 단어 분석**")
            col_sent1, col_sent2 = st.columns(2)

            with col_sent1:
                st.metric("😊 긍정 단어 감지 횟수", f"{pos_count}회")
                unique_pos = list(set(pos_found))
                st.caption(f"발견된 긍정 단어: {', '.join(unique_pos) if unique_pos else '없음'}")

            with col_sent2:
                st.metric("😢 부정 단어 감지 횟수", f"{neg_count}회")
                unique_neg = list(set(neg_found))
                st.caption(f"발견된 부정 단어: {', '.join(unique_neg) if unique_neg else '없음'}")

            # 3) 긍정/부정 비교 원그래프(파이 차트)
            if pos_count > 0 or neg_count > 0:
                sentiment_df = pd.DataFrame({
                    "감성": ["긍정", "부정"],
                    "단어 수": [pos_count, neg_count]
                })
                fig_pie = px.pie(
                    sentiment_df,
                    names="감성",
                    values="단어 수",
                    title="긍정 vs 부정 단어 비율",
                    color="감성",
                    color_discrete_map={"긍정": "#4CAF50", "부정": "#FF5252"}
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("데이터에서 지정된 긍정/부정 단어를 찾지 못했습니다.")
        else:
            st.info("선택된 학과에 작성된 한줄의견이 없습니다.")
    else:
        st.warning("CSV 파일에 '한줄의견' (또는 '의견') 컬럼이 없습니다.")

else:
    st.info("좌측 상단에서 분석할 CSV 파일을 업로드해 주세요.")