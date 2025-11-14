"""
바이낸스 카피트레이딩 시스템 GUI 런처
간단한 버튼 클릭으로 시스템 실행
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import os
import sys
import threading
from pathlib import Path


class TradingLauncher:
    """카피트레이딩 시스템 런처 GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("바이낸스 카피트레이딩 시스템 런처")
        self.root.geometry("600x700")
        self.root.resizable(False, False)

        # 프로세스 추적
        self.process = None
        self.is_running = False

        # UI 생성
        self.create_ui()

        # 초기 상태 확인
        self.check_environment()

    def create_ui(self):
        """UI 구성"""
        # 타이틀
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title = tk.Label(
            title_frame,
            text="🚀 바이낸스 카피트레이딩 시스템",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title.pack(expand=True)

        # 메인 컨테이너
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 환경 상태
        status_frame = tk.LabelFrame(main_frame, text="환경 상태", padx=10, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(
            status_frame,
            text="환경 확인 중...",
            font=("Arial", 10),
            anchor="w"
        )
        self.status_label.pack(fill=tk.X)

        # 실행 모드 선택
        mode_frame = tk.LabelFrame(main_frame, text="실행 모드 선택", padx=10, pady=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.mode_var = tk.StringVar(value="api")

        # API 서버 모드
        api_radio = tk.Radiobutton(
            mode_frame,
            text="🌐 API 서버 (웹 대시보드)",
            variable=self.mode_var,
            value="api",
            font=("Arial", 10, "bold")
        )
        api_radio.pack(anchor=tk.W, pady=(5, 0))

        api_desc = tk.Label(
            mode_frame,
            text="   → 웹 브라우저에서 http://localhost:8000 으로 모니터링\n"
                 "   → 실시간 차트, 거래 내역, 수동 제어 가능\n"
                 "   → 처음 사용하시면 이 모드를 선택하세요!",
            font=("Arial", 8),
            anchor="w",
            justify=tk.LEFT,
            fg="#555"
        )
        api_desc.pack(anchor=tk.W, pady=(0, 5))

        # 자동 거래 모드
        auto_radio = tk.Radiobutton(
            mode_frame,
            text="🤖 자동 거래 모드",
            variable=self.mode_var,
            value="auto",
            font=("Arial", 10, "bold")
        )
        auto_radio.pack(anchor=tk.W, pady=(5, 0))

        auto_desc = tk.Label(
            mode_frame,
            text="   → 백그라운드에서 자동으로 신호 감지 & 거래 실행\n"
                 "   → 웹 대시보드 없이 실행 (로그로만 확인)\n"
                 "   → 장기 운영용, 충분히 테스트 후 사용하세요!",
            font=("Arial", 8),
            anchor="w",
            justify=tk.LEFT,
            fg="#555"
        )
        auto_desc.pack(anchor=tk.W, pady=(0, 5))

        # 설정 정보
        config_frame = tk.LabelFrame(main_frame, text="⚙️ 설정 파일 편집", padx=10, pady=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        config_info = tk.Label(
            config_frame,
            text="시작하기 전에 꼭 설정하세요!\n\n"
                 "• .env: Binance API 키 입력 (필수!)\n"
                 "• config.yaml: 거래 전략, 리스크 설정 등\n\n"
                 "⚠️ Testnet 모드 사용을 권장합니다 (실제 돈 없이 테스트)",
            font=("Arial", 9),
            anchor="w",
            justify=tk.LEFT,
            fg="#d35400"
        )
        config_info.pack(fill=tk.X, pady=(0, 10))

        tk.Button(
            config_frame,
            text="📝 .env 파일 편집",
            command=self.edit_env,
            width=20
        ).pack(pady=5)

        tk.Button(
            config_frame,
            text="⚙️ config.yaml 편집",
            command=self.edit_config,
            width=20
        ).pack(pady=5)

        # 제어 버튼
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = tk.Button(
            button_frame,
            text="▶️ 시작",
            command=self.start_system,
            bg="#27ae60",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            cursor="hand2"
        )
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_button = tk.Button(
            button_frame,
            text="⏹️ 중지",
            command=self.stop_system,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        # 빠른 접속 버튼 (API 모드용)
        self.dashboard_button = tk.Button(
            main_frame,
            text="🌐 웹 대시보드 열기 (http://localhost:8000)",
            command=self.open_dashboard,
            state=tk.DISABLED
        )
        self.dashboard_button.pack(fill=tk.X, pady=(0, 10))

        # 로그 출력
        log_frame = tk.LabelFrame(main_frame, text="시스템 로그", padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 상태바
        self.status_bar = tk.Label(
            self.root,
            text="준비",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#ecf0f1"
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def check_environment(self):
        """환경 확인"""
        issues = []

        # .env 파일 확인 및 자동 생성
        if not os.path.exists(".env"):
            if os.path.exists(".env.example"):
                try:
                    import shutil
                    shutil.copy(".env.example", ".env")
                    issues.append("✅ .env 파일 자동 생성됨 (편집 필요!)")
                    self.log("⚠️ .env 파일을 생성했습니다. Binance API 키를 입력해주세요!")
                    # 자동으로 편집 창 열기
                    self.root.after(1000, self.edit_env)
                except Exception as e:
                    issues.append(f"❌ .env 파일 생성 실패: {e}")
            else:
                issues.append("❌ .env.example 파일이 없습니다")
        else:
            issues.append("✅ .env 파일 존재")

        # config.yaml 확인
        if not os.path.exists("config.yaml"):
            issues.append("❌ config.yaml 파일이 없습니다")
        else:
            issues.append("✅ config.yaml 파일 존재")

        # Python 확인
        try:
            version = sys.version.split()[0]
            issues.append(f"✅ Python {version}")
        except:
            issues.append("❌ Python 확인 실패")

        status_text = "\n".join(issues)
        self.status_label.config(text=status_text)
        self.log(status_text)

    def start_system(self):
        """시스템 시작"""
        if self.is_running:
            messagebox.showwarning("경고", "이미 실행 중입니다")
            return

        # 모드 확인
        mode = "1" if self.mode_var.get() == "api" else "2"
        mode_name = "API 서버" if mode == "1" else "자동 거래"

        self.log(f"\n{'='*50}")
        self.log(f"시스템 시작: {mode_name} 모드")
        self.log(f"{'='*50}")

        # 버튼 상태 변경
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        if mode == "1":
            self.dashboard_button.config(state=tk.NORMAL)

        # 백그라운드에서 실행
        thread = threading.Thread(target=self._run_system, args=(mode,), daemon=True)
        thread.start()

        self.is_running = True
        self.status_bar.config(text=f"실행 중: {mode_name} 모드")

    def _run_system(self, mode):
        """시스템 실행 (백그라운드 스레드)"""
        try:
            # Python 실행 명령
            python_cmd = sys.executable
            script_path = "main.py"

            # 프로세스 시작
            self.process = subprocess.Popen(
                [python_cmd, script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # 모드 선택 입력
            if self.process.stdin:
                self.process.stdin.write(f"{mode}\n")
                self.process.stdin.flush()

            # 출력 읽기
            for line in self.process.stdout:
                self.log(line.strip())

        except Exception as e:
            self.log(f"❌ 오류: {e}")
            messagebox.showerror("오류", f"시스템 시작 실패:\n{e}")
        finally:
            self.is_running = False
            self.root.after(0, self._on_process_end)

    def stop_system(self):
        """시스템 중지"""
        if not self.is_running or not self.process:
            return

        if messagebox.askyesno("확인", "시스템을 중지하시겠습니까?"):
            self.log("\n시스템 중지 중...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()

            self._on_process_end()

    def _on_process_end(self):
        """프로세스 종료 후 처리"""
        self.is_running = False
        self.process = None

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.dashboard_button.config(state=tk.DISABLED)

        self.status_bar.config(text="중지됨")
        self.log("\n시스템 종료됨")

    def open_dashboard(self):
        """웹 대시보드 열기"""
        import webbrowser
        webbrowser.open("http://localhost:8000")
        self.log("웹 브라우저에서 대시보드를 열었습니다")

    def edit_env(self):
        """환경 변수 파일 편집"""
        self._open_file(".env")

    def edit_config(self):
        """설정 파일 편집"""
        self._open_file("config.yaml")

    def _open_file(self, filename):
        """파일 편집기로 열기"""
        if not os.path.exists(filename):
            if filename == ".env" and os.path.exists(".env.example"):
                # .env.example을 복사
                import shutil
                shutil.copy(".env.example", ".env")
                messagebox.showinfo("정보", ".env.example을 복사하여 .env 파일을 생성했습니다")
            else:
                messagebox.showwarning("경고", f"{filename} 파일이 없습니다")
                return

        # OS별 편집기 실행
        if sys.platform == "win32":
            os.startfile(filename)
        elif sys.platform == "darwin":
            subprocess.run(["open", filename])
        else:
            subprocess.run(["xdg-open", filename])

        self.log(f"{filename} 파일을 편집기로 열었습니다")

    def log(self, message):
        """로그 출력"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.update()


def main():
    """메인 함수"""
    # 프로젝트 루트로 이동
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # GUI 시작
    root = tk.Tk()
    app = TradingLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
