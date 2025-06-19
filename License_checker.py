import requests
import datetime
import hashlib
import platform
import base64
import json

class OnlineLicenseManager:
    def __init__(self, github_repo="THKKANON/Debug_Timer", license_file_path="license_info.json"):
        self.github_repo = github_repo
        self.file_path = license_file_path
        repo_parts = github_repo.split('/')
        self.owner = repo_parts[0]
        self.repo = repo_parts[1]
        self.api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{license_file_path}"
    
    def _get_machine_id(self):
        """기기 고유 ID 생성 (라이센스 검증에 사용)"""
        try:
            if platform.system() == 'Linux':
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
            elif platform.system() == 'Windows':
                import subprocess
                result = subprocess.check_output('wmic csproduct get uuid').decode()
                machine_id = result.split('\n')[1].strip()
            elif platform.system() == 'Darwin':  # macOS
                import subprocess
                result = subprocess.check_output(['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice']).decode()
                for line in result.split('\n'):
                    if 'IOPlatformUUID' in line:
                        machine_id = line.split('"')[3]
                        break
            else:
                # 알 수 없는 OS의 경우
                machine_id = platform.node()
            
            # 시스템 정보로 보강
            system_info = f"{platform.node()}{platform.processor()}{platform.machine()}"
            combined = machine_id + system_info
            
            # SHA-256 해시로 반환
            return hashlib.sha256(combined.encode()).hexdigest()
            
        except Exception as e:
            print(f"기기 ID 생성 오류: {e}")
            # 오류 시 기본값 (보안성 낮음)
            fallback = f"{platform.node()}-{platform.processor()}"
            return hashlib.sha256(fallback.encode()).hexdigest()
    
    def fetch_license_data(self):
        """GitHub API를 사용하여 라이센스 정보 가져오기"""
        try:
            session = requests.Session()
            session.headers.update({
                'Cache-Control': 'no-cache',
                'Accept': 'application/vnd.github.v3+json'
            })
            response = session.get(self.api_url, timeout=10)
            
            if response.status_code == 200:
                content_data = response.json()
                # Base64로 인코딩된 콘텐츠 디코딩
                content = base64.b64decode(content_data['content']).decode('utf-8')
                license_data = json.loads(content)
                return license_data
            else:
                print(f"라이센스 정보를 가져오는데 실패했습니다. 상태 코드: {response.status_code}")
                print(f"API URL: {self.api_url}")
                print(f"응답 내용: {response.text[:200]}...")  # 응답 내용 일부 출력
                return None
                
        except requests.exceptions.Timeout:
            print("라이센스 서버 연결 시간이 초과되었습니다.")
            return None
        except requests.exceptions.ConnectionError:
            print("인터넷 연결이 없거나 GitHub에 연결할 수 없습니다.")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return None
        except Exception as e:
            print(f"온라인 라이센스 정보 가져오기 오류: {e}")
            return None
    
    def get_license_for_machine(self, licenses_data):
        """기기 ID에 맞는 라이센스 찾기"""
        machine_id = self._get_machine_id()
        
        # 라이센스 데이터에서 현재 기기 ID에 맞는 항목 찾기
        for license_item in licenses_data.get("licenses", []):
            if license_item.get("machine_id") == machine_id:
                return license_item
        
        # 모든 기기에 적용되는 글로벌 라이센스 찾기
        for license_item in licenses_data.get("licenses", []):
            if license_item.get("type") == "global":
                return license_item
        
        return None
    
    def validate_license(self):
        """라이센스 유효성 검사 (온라인 전용)"""
        try:
            # 1. 온라인으로 라이센스 정보 가져오기
            online_licenses = self.fetch_license_data()
            
            if not online_licenses:
                print("온라인에서 라이센스 정보를 가져올 수 없습니다.")
                return False
            
            # 2. 해당 기기에 맞는 라이센스 찾기
            license_data = self.get_license_for_machine(online_licenses)
            
            # 3. 라이센스가 없으면 실패
            if not license_data:
                print("이 기기에 유효한 라이센스를 찾을 수 없습니다.")
                return False
            
            # 4. 만료일 확인
            expiry_date = datetime.datetime.strptime(license_data.get("expiry_date", "2000-01-01"), "%Y-%m-%d").date()
            current_date = datetime.datetime.now().date()

            if current_date > expiry_date:
                return False
            
            # 5. 추가 라이센스 제한 확인
            elif license_data.get("disabled", False):
                return False
            
            # 6. 유효한 라이센스
            else:
                return True
            
        except Exception as e:
            print(f"라이센스 검증 오류: {e}")
            return False