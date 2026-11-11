"""kitlib — 표준 라이브러리 전용 빌딩블록 (Python 3.8+, 외부 의존성 없음).

  csvio timeparse quality profile            읽기·품질
  rules stats_detect alerts spc              판정·탐지·경보·관리도
  groupstats schedule logparse reconcile     요인 집계·디스패칭·로그·대사
  report svgchart webapp cli                 리포트·SVG·서버·CLI
  synth evalmetrics                          합성 데이터·지표
  csvschema dbcore webcore                   CSV 묶음 검증·SQLite·미니 웹 프레임워크 (서비스형)
  geo vrp verify                             좌표·배정/묶음/시간표·규칙 검증기 골격
  overlay                                    오버레이 성분 분해·지표·flyer·벡터맵
쓰는 모듈만 남겨도 된다. 사용 시 출처(kitlib/<모듈>)를 기록한다.
"""

__version__ = "0.4.0"
