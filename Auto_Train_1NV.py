"""Auto Train Mil và Cổ Mộ — 1 nhân vật, bản thử nghiệm không kích hoạt.
Chỉ Windows; đọc ảnh cửa sổ đang hiển thị; không đọc bộ nhớ game.
"""
import ctypes
from ctypes import wintypes
import json
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageGrab, ImageTk
import numpy as np

if sys.platform != 'win32':
    raise SystemExit('Ứng dụng này chỉ hỗ trợ Windows 10/11.')

u = ctypes.windll.user32
u.SetProcessDPIAware()
WM_KEYDOWN, WM_KEYUP, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x100, 0x101, 0x201, 0x202
VK = {'Tab': 0x09, 'Space': 0x20, **{str(i): 0x30+i for i in range(10)}}
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
CONFIG = Path.home() / 'AutoTrainMil1NV_config.json'

class RECT(ctypes.Structure):
    _fields_ = [('left',ctypes.c_long),('top',ctypes.c_long),('right',ctypes.c_long),('bottom',ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [('x',ctypes.c_long),('y',ctypes.c_long)]

ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
u.EnumWindows.argtypes = [ENUMPROC, wintypes.LPARAM]
u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
u.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
u.PostMessageW.restype = wintypes.BOOL

def windows():
    out = []
    def cb(hwnd, unused):
        if not u.IsWindowVisible(hwnd): return True
        n = u.GetWindowTextLengthW(hwnd)
        if not n: return True
        buf = ctypes.create_unicode_buffer(n+1)
        u.GetWindowTextW(hwnd, buf, n+1)
        name = buf.value.strip()
        if name and 'Auto Train Mil' not in name:
            out.append((f'{name[:42]} [HWND {int(hwnd)}]', int(hwnd)))
        return True
    callback = ENUMPROC(cb)
    u.EnumWindows(callback, 0)
    return out

def client_box(hwnd):
    r=RECT()
    if not u.IsWindow(hwnd) or not u.GetClientRect(hwnd, ctypes.byref(r)): return None
    p=POINT(0,0)
    if not u.ClientToScreen(hwnd, ctypes.byref(p)): return None
    w,h=r.right-r.left,r.bottom-r.top
    if w<150 or h<150: return None
    return (p.x,p.y,p.x+w,p.y+h)

def screenshot(hwnd):
    box=client_box(hwnd)
    if box is None or u.IsIconic(hwnd): return None
    try: return ImageGrab.grab(bbox=box, all_screens=True).convert('RGB')
    except Exception: return None

def key(hwnd, v):
    if not u.IsWindow(hwnd): return False
    # Lparam contains a basic scan code; some games ignore background messages.
    scan = u.MapVirtualKeyW(v,0)
    return bool(u.PostMessageW(hwnd,WM_KEYDOWN,v,1 | (scan<<16)) and
                u.PostMessageW(hwnd,WM_KEYUP,v,0xC0000001 | (scan<<16)))

def click(hwnd, x, y):
    box=client_box(hwnd)
    if not box: return False
    w,h=box[2]-box[0],box[3]-box[1]
    x=max(1,min(w-2,int(x))); y=max(1,min(h-2,int(y)))
    lp=(y<<16)|(x & 0xffff)
    return bool(u.PostMessageW(hwnd,WM_LBUTTONDOWN,1,lp) and u.PostMessageW(hwnd,WM_LBUTTONUP,0,lp))

class App:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title('Auto Train Mil và Cổ Mộ — 1 nhân vật')
        self.root.geometry('650x790')
        self.root.resizable(False,False)
        self.root.configure(bg='#e9f4ff')
        self.running=threading.Event()
        self.thread=None
        self.items={}
        self.hwnds={}
        self.roi=None
        self.no_target=None
        self.yes_target=None
        self.load()
        self.build()
        self.root.protocol('WM_DELETE_WINDOW',self.close)

    def load(self):
        self.data={}
        try: self.data=json.loads(CONFIG.read_text(encoding='utf-8'))
        except (OSError,ValueError): pass
        self.roi=self.data.get('roi')
        self.no_target=self.data.get('no_target')
        self.yes_target=self.data.get('yes_target')

    def save(self):
        data={'roi':self.roi,'no_target':self.no_target,'yes_target':self.yes_target,
              'enabled':{k:v.get() for k,v in self.checks.items()},
              'intervals':{k:v.get() for k,v in self.intervals.items()}}
        try: CONFIG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError: pass

    def build(self):
        if (ROOT/'header.png').exists():
            im=Image.open(ROOT/'header.png').convert('RGB')
            self.header=ImageTk.PhotoImage(im)
            tk.Label(self.root,image=self.header,bd=0).pack()
        else:
            tk.Label(self.root,text='Auto Train Mil và Cổ Mộ',font=('Segoe UI',19,'bold'),fg='#0758a5',bg='#e9f4ff').pack(pady=15)
        tk.Label(self.root,text='Zalo: TuanHo – 0398438721  |  BẢN 1 NHÂN VẬT • KHÔNG KEY',font=('Segoe UI',10,'bold'),fg='#0758a5',bg='#e9f4ff').pack(pady=3)
        frame=tk.LabelFrame(self.root,text='NHÂN VẬT 1',bg='white',fg='#0865ad',font=('Segoe UI',12,'bold'),padx=13,pady=10)
        frame.pack(fill='x',padx=14,pady=9)
        row=tk.Frame(frame,bg='white');row.pack(fill='x')
        self.window=tk.StringVar()
        self.combo=ttk.Combobox(row,textvariable=self.window,state='readonly',width=48)
        self.combo.pack(side='left',fill='x',expand=True)
        ttk.Button(row,text='Làm mới',command=self.refresh).pack(side='left',padx=6)
        self.refresh()
        self.checks={};self.intervals={}
        left=['Tìm Quái','Nhặt Đồ','Skill 1','Skill 2','Skill 3','Skill 4']
        right=['Skill 5','Skill 6','Skill 7','Bay chỗ khác (8)','Bơm Máu (9)','Bơm Mana (0)']
        columns=tk.Frame(frame,bg='white');columns.pack(fill='x',pady=(10,4))
        for ci,labels in enumerate((left,right)):
            col=tk.Frame(columns,bg='white');col.grid(row=0,column=ci,sticky='nw',padx=(0,14) if ci==0 else (8,0))
            for i,label in enumerate(labels):
                name=label
                var=tk.BooleanVar(value=self.data.get('enabled',{}).get(name,True))
                self.checks[name]=var
                tk.Checkbutton(col,text=label,variable=var,bg='white',anchor='w',font=('Segoe UI',9),width=18 if ci==0 else 20).grid(row=i,column=0,sticky='w',pady=3)
                if name not in ('Tìm Quái','Nhặt Đồ'):
                    default='180' if name=='Bay chỗ khác (8)' else '2'
                    v=tk.StringVar(value=self.data.get('intervals',{}).get(name,default))
                    self.intervals[name]=v
                    tk.Entry(col,textvariable=v,width=6,justify='center',font=('Segoe UI',9)).grid(row=i,column=1,padx=(1,0))
        self.auto=tk.Button(frame,text='▶ BẬT AUTO',command=self.toggle,bg='#21a95e',fg='white',activebackground='#148349',font=('Segoe UI',12,'bold'),height=2)
        self.auto.pack(fill='x',pady=(10,0))
        area=tk.LabelFrame(self.root,text='TỰ DI CHUYỂN TÌM QUÁI (thử nghiệm)',bg='white',fg='#0865ad',font=('Segoe UI',10,'bold'),padx=12,pady=10)
        area.pack(fill='x',padx=14,pady=6)
        self.move=tk.BooleanVar(value=True)
        tk.Checkbutton(area,text='Di chuyển quanh vị trí đứng khi không có mục tiêu',variable=self.move,bg='white').pack(anchor='w')
        ttk.Button(area,text='1. Chọn vùng thanh máu / tên quái',command=self.choose_roi).pack(fill='x',pady=(8,3))
        r=tk.Frame(area,bg='white');r.pack(fill='x')
        ttk.Button(r,text='2. Ghi mẫu KHÔNG quái',command=lambda:self.calibrate(False)).pack(side='left',expand=True,fill='x',padx=(0,4))
        ttk.Button(r,text='3. Ghi mẫu CÓ quái',command=lambda:self.calibrate(True)).pack(side='left',expand=True,fill='x',padx=(4,0))
        self.status=tk.StringVar(value='Chưa chạy. Cần chọn vùng và ghi 2 mẫu trước khi tự di chuyển.')
        tk.Label(self.root,textvariable=self.status,bg='#e9f4ff',fg='#12446a',wraplength=610,justify='left',font=('Segoe UI',9)).pack(padx=16,pady=10,anchor='w')
        tk.Label(self.root,text='Tab: 3,5s  •  Nhặt Đồ: Space 0,1s (ẩn)  •  Bay: 180s',bg='#e9f4ff',fg='#42627c').pack(pady=3)
        tk.Label(self.root,text='Cần để cửa sổ game hiện trên màn hình khi nhận diện ảnh.',bg='#e9f4ff',fg='#9a5021').pack(pady=2)

    def refresh(self):
        opts=windows();self.hwnds=dict(opts)
        self.combo['values']=list(self.hwnds)
        if opts: self.window.set(opts[0][0])

    def hwnd(self):return self.hwnds.get(self.window.get())

    def choose_roi(self):
        hwnd=self.hwnd()
        im=screenshot(hwnd) if hwnd else None
        if im is None:
            messagebox.showwarning('Không chụp được','Hãy mở game, đưa cửa sổ lên màn hình và không thu nhỏ.');return
        # Screenshot shown at up to 620x400; drag to mark health/name target only.
        scale=min(620/im.width,400/im.height,1)
        shown=im.resize((int(im.width*scale),int(im.height*scale)))
        popup=tk.Toplevel(self.root);popup.title('Kéo chuột khoanh vùng tên/thanh máu quái')
        photo=ImageTk.PhotoImage(shown);cv=tk.Canvas(popup,width=shown.width,height=shown.height,cursor='cross')
        cv.pack();cv.create_image(0,0,anchor='nw',image=photo);cv.image=photo
        state={'start':None,'rect':None}
        def down(e):state['start']=(e.x,e.y)
        def drag(e):
            if state['start'] is None:return
            if state['rect']:cv.delete(state['rect'])
            x,y=state['start'];state['rect']=cv.create_rectangle(x,y,e.x,e.y,outline='red',width=2)
        def up(e):
            if state['start'] is None:return
            x,y=state['start'];x1,x2=sorted((x,e.x));y1,y2=sorted((y,e.y))
            if x2-x1<15 or y2-y1<8:return
            self.roi=[x1/shown.width,y1/shown.height,x2/shown.width,y2/shown.height]
            self.no_target=None;self.yes_target=None
            self.save();self.status.set('Đã chọn vùng. Hãy ghi mẫu KHÔNG quái rồi CÓ quái.');popup.destroy()
        cv.bind('<ButtonPress-1>',down);cv.bind('<B1-Motion>',drag);cv.bind('<ButtonRelease-1>',up)

    def red_score(self,im):
        if not self.roi:return None
        w,h=im.size
        x1,y1,x2,y2=self.roi
        box=(int(x1*w),int(y1*h),int(x2*w),int(y2*h))
        if box[2]-box[0]<4 or box[3]-box[1]<4:return None
        arr=np.asarray(im.crop(box),dtype=np.int16)
        r,g,b=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        # Detect saturated red health bar. UI must be calibrated per game window.
        return float(np.mean((r>100)&(r>g*1.45)&(r>b*1.4)&((r-g)>35)))

    def calibrate(self,yes):
        hwnd=self.hwnd();im=screenshot(hwnd) if hwnd else None
        if not self.roi or im is None:
            messagebox.showwarning('Chưa sẵn sàng','Chọn vùng thanh máu trước và giữ cửa sổ game hiển thị.');return
        score=self.red_score(im)
        if yes:self.yes_target=score
        else:self.no_target=score
        self.save();self.status.set(f'Đã ghi mẫu {"CÓ" if yes else "KHÔNG"} quái: mức đỏ {score:.4f}.')
        if self.no_target is not None and self.yes_target is not None and abs(self.yes_target-self.no_target)<0.008:
            messagebox.showwarning('Mẫu chưa phân biệt được','Hai mẫu gần giống nhau. Hãy khoanh sát thanh máu đỏ, rồi ghi lại cả hai mẫu.')

    def has_target(self,im):
        if im is None or self.no_target is None or self.yes_target is None:return None
        if abs(self.yes_target-self.no_target)<0.008:return None
        score=self.red_score(im)
        if score is None:return None
        midpoint=(self.yes_target+self.no_target)/2
        return score>midpoint if self.yes_target>self.no_target else score<midpoint

    def toggle(self):
        if self.running.is_set():
            self.running.clear();self.auto.config(text='▶ BẬT AUTO',bg='#21a95e');self.status.set('Đã yêu cầu dừng Auto.');return
        hwnd=self.hwnd()
        if not hwnd or not u.IsWindow(hwnd):
            messagebox.showwarning('Thiếu cửa sổ','Chọn đúng cửa sổ game.');return
        intervals={}
        for name,var in self.intervals.items():
            try:
                value=float(var.get().replace(',','.'))
                if not 0.1<=value<=10800:raise ValueError()
            except ValueError:
                messagebox.showwarning('Sai thời gian',f'{name}: nhập số từ 0,1 đến 10800 giây.');return
            intervals[name]=value
        if self.move.get() and self.checks['Tìm Quái'].get() and (self.roi is None or self.no_target is None or self.yes_target is None or abs(self.yes_target-self.no_target)<0.008):
            messagebox.showwarning('Chưa hiệu chỉnh','Để tự di chuyển, hãy chọn vùng thanh máu và ghi đủ 2 mẫu khác nhau; hoặc bỏ tích Tự di chuyển.');return
        self.save()
        flags={k:v.get() for k,v in self.checks.items()}
        self.running.set();self.auto.config(text='■ TẮT AUTO',bg='#d44545')
        self.thread=threading.Thread(target=self.worker,args=(hwnd,flags,intervals,self.move.get()),daemon=True)
        self.thread.start()

    def report(self,msg):
        try:self.root.after(0,lambda:self.status.set(msg))
        except RuntimeError:pass

    def worker(self,hwnd,flags,intervals,moving):
        now=time.monotonic()
        next_due={name:now for name,enabled in flags.items() if enabled}
        # 6 short relative screen moves, not absolute map coordinates.
        offsets=[(0.16,0.14),(-0.14,0.12),(-0.17,-0.10),(0.13,-0.14),(0.10,0.08),(-0.10,-0.07)]
        step=0;next_move=now+3;last_image=0;target=None
        while self.running.is_set() and u.IsWindow(hwnd):
            now=time.monotonic()
            if moving and flags.get('Tìm Quái') and now-last_image>=0.5:
                target=self.has_target(screenshot(hwnd));last_image=now
            for name in list(next_due):
                period=3.5 if name=='Tìm Quái' else 0.1 if name=='Nhặt Đồ' else intervals[name]
                if now>=next_due[name]:
                    vk=VK['Tab'] if name=='Tìm Quái' else VK['Space'] if name=='Nhặt Đồ' else VK[name.split()[-1].strip('()')] if name.startswith(('Bay','Bơm')) else VK[name.split()[-1]]
                    key(hwnd,vk)
                    next_due[name]=now+period
            if moving and flags.get('Tìm Quái') and target is False and now>=next_move:
                box=client_box(hwnd)
                if box:
                    w,h=box[2]-box[0],box[3]-box[1]
                    dx,dy=offsets[step%len(offsets)]
                    # Click within central ground area. Needs field testing.
                    click(hwnd,w*(0.5+dx),h*(0.58+dy))
                    step+=1;self.report(f'Chưa có quái — thử di chuyển điểm {step%len(offsets)+1}.')
                next_move=now+3.0
            elif target is True and now>=next_move:
                self.report('Đã thấy thanh máu quái — ngừng ra lệnh di chuyển, tiếp tục đánh.')
                next_move=now+3.0
            time.sleep(0.02)
        self.running.clear()
        self.report('Auto đã dừng (hoặc cửa sổ game đã đóng).')
        try:self.root.after(0,lambda:self.auto.config(text='▶ BẬT AUTO',bg='#21a95e'))
        except RuntimeError:pass

    def close(self):
        self.running.clear();self.save();self.root.destroy()

if __name__=='__main__':
    App().root.mainloop()
