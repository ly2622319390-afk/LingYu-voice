/**
 * Python 后端子进程管理器
 *
 * 职责:
 * 1. 启动 uvicorn 作为子进程
 * 2. 等待端口就绪
 * 3. 监控进程健康，崩溃时自动重启
 * 4. 应用退出时优雅关闭
 */
import { spawn, spawnSync, ChildProcess } from 'child_process';
import { app } from 'electron';
import * as path from 'path';
import * as http from 'http';
import * as fs from 'fs';

const BACKEND_PORT = 8000;
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`;
const MAX_RESTART_ATTEMPTS = 3;
const RESTART_DELAY_MS = 2000;

export class BackendManager {
  private process: ChildProcess | null = null;
  private restartAttempts = 0;
  private _ready = false;

  get ready(): boolean {
    return this._ready;
  }

  get port(): number {
    return BACKEND_PORT;
  }

  /**
   * 启动 Python 后端
   */
  async start(): Promise<void> {
    // 查找可用的 Python 命令
    const pythonCmd = this.findPython();

    // 项目根目录 = Electron 应用目录的父级（开发时）或 extraResources（打包后）
    const backendDir = this.getBackendDir();

    if (!fs.existsSync(backendDir)) {
      console.warn(`[Backend] 后端目录不存在: ${backendDir}，跳过子进程启动`);
      console.warn('[Backend] 请确保后端已手动启动: cd backend && uvicorn main:app --port 8000');
      return;
    }

    console.log(`[Backend] 启动: ${pythonCmd} -m uvicorn main:app --port ${BACKEND_PORT}`);
    console.log(`[Backend] 工作目录: ${backendDir}`);

    this.process = spawn(pythonCmd, [
      '-m', 'uvicorn', 'main:app',
      '--host', '127.0.0.1',
      '--port', String(BACKEND_PORT),
      '--log-level', 'warning',
    ], {
      cwd: backendDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });

    this.process.stdout?.on('data', (data) => {
      console.log(`[Backend] ${data.toString().trim()}`);
    });

    this.process.stderr?.on('data', (data) => {
      console.log(`[Backend] ${data.toString().trim()}`);
    });

    this.process.on('exit', (code) => {
      console.log(`[Backend] 进程退出 (code=${code})`);
      this._ready = false;
      this.process = null;

      if (code !== 0 && this.restartAttempts < MAX_RESTART_ATTEMPTS) {
        this.restartAttempts++;
        console.log(`[Backend] ${RESTART_DELAY_MS}ms 后重启 (${this.restartAttempts}/${MAX_RESTART_ATTEMPTS})`);
        setTimeout(() => this.start(), RESTART_DELAY_MS);
      }
    });

    // 等待后端就绪
    await this.waitForReady();
  }

  /**
   * 等待后端健康检查通过
   */
  private async waitForReady(timeoutMs = 30000): Promise<void> {
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {
      try {
        await this.httpGet(HEALTH_URL);
        this._ready = true;
        this.restartAttempts = 0;
        console.log('[Backend] 后端就绪');
        return;
      } catch {
        await this.delay(500);
      }
    }

    console.warn('[Backend] 后端启动超时，继续运行（可能需手动启动）');
  }

  /**
   * 停止后端进程
   */
  stop(): void {
    if (this.process) {
      console.log('[Backend] 正在关闭...');
      if (process.platform === 'win32') {
        // Windows 用 taskkill 杀死进程树
        spawn('taskkill', ['/pid', String(this.process.pid), '/f', '/t']);
      } else {
        this.process.kill('SIGTERM');
      }
      this.process = null;
      this._ready = false;
    }
  }

  private findPython(): string {
    const candidates = ['python', 'python3', 'py'];
    for (const cmd of candidates) {
      try {
        const result = spawnSync(cmd, ['--version'], { encoding: 'utf-8' });
        if (result.status === 0) return cmd;
      } catch {
        continue;
      }
    }
    return 'python'; // 默认
  }

  private getBackendDir(): string {
    if (app.isPackaged) {
      // 打包后: extraResources/backend/
      return path.join(process.resourcesPath, 'backend');
    }
    // 开发时: 项目根目录/backend/
    return path.join(app.getAppPath(), '..', 'backend');
  }

  private httpGet(url: string): Promise<string> {
    return new Promise((resolve, reject) => {
      http.get(url, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => resolve(data));
      }).on('error', reject);
    });
  }

  private delay(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }
}
