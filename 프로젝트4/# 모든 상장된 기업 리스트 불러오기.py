# 모든 상장된 기업 리스트 불러오기
import dart_fss as dart
API_KEY = "74adc2784f44295c44d335e4f11ab1e6178c336e"
dart.set_api_key(api_key=API_KEY)
corp_list = dart.get_corp_list()

# 삼성전자를 이름으로 찾기 ( 리스트 반환 )
Taesung = corp_list.find_by_corp_name('태성', exactly=True)[0]
print(Taesung)