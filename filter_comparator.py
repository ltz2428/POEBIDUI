import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import re

class FilterComparatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("POE 过滤器同步编辑器 v11.0 - 精准定位版")
        self.root.geometry("1850x950")
        self.root.configure(bg="#f5f6f7")

        # 样式参数
        self.ui_font = ("Consolas", 15)
        self.btn_font = ("Consolas", 11, "bold")
        self.line_spacing = 6
        self.palette = ["#e8f5e9", "#e3f2fd", "#fff3e0", "#f3e5f5", "#f1f8e9", "#e0f2f1", "#eceff1", "#efebe9"]
        self.primary_color = "#2c3e50"
        self.accent_color = "#2ecc71"

        self.main_file_path = tk.StringVar()
        self.comp_file_path = tk.StringVar()
        
        self.search_indices = {} 
        self.tag_metadata = {} 
        self.current_main_locate = None 
        self.current_comp_locate = None 

        self.columns = [] 

        self.setup_ui()

    def setup_ui(self):
        # Top Global Toolbar
        toolbar = tk.Frame(self.root, bg=self.primary_color, pady=10)
        toolbar.pack(fill=tk.X)

        tk.Label(toolbar, text="POE 编辑器 v11.0", font=("Consolas", 14, "bold"), fg="white", bg=self.primary_color).pack(side=tk.LEFT, padx=20)
        
        btn_opts = {"font": self.btn_font, "relief": tk.FLAT, "padx": 25, "pady": 8}
        
        self.btn_replace = tk.Button(toolbar, text="⚡ 替换 BaseType", command=self.replace_basetype_logic, 
                                     bg="#e67e22", fg="white", **btn_opts)
        self.btn_replace.pack(side=tk.RIGHT, padx=20)

        tk.Button(toolbar, text="🔍 开始比对", command=self.run_comparison, bg=self.accent_color, fg="white", **btn_opts).pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="📂 比对文件", command=lambda: self.browse_file(self.comp_file_path), **btn_opts).pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="📂 主文件", command=lambda: self.browse_file(self.main_file_path), **btn_opts).pack(side=tk.RIGHT, padx=5)

        # 核心：横向四栏 PanedWindow
        self.workspace = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#dcdde1", sashwidth=4)
        self.workspace.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.col_configs = [
            {"title": "1. 主原文件 (编辑)", "is_orig": True, "path_var": self.main_file_path, "is_main": True},
            {"title": "2. 主多出内容 (结果)", "is_orig": False, "is_main": True},
            {"title": "3. 比对多出内容 (结果)", "is_orig": False, "is_main": False},
            {"title": "4. 比对原文件 (编辑)", "is_orig": True, "path_var": self.comp_file_path, "is_main": False}
        ]
        
        for cfg in self.col_configs:
            col_frame = self.create_unified_column(cfg)
            self.columns.append(col_frame)
            self.workspace.add(col_frame, stretch="always")

    def create_unified_column(self, cfg):
        frame = tk.Frame(self.workspace, bg="#fafafa")
        
        head = tk.Frame(frame, bg="#ecf0f1", pady=2)
        head.pack(fill=tk.X)
        
        # [左侧固定元素]
        tk.Label(head, text=cfg["title"], font=("Consolas", 10, "bold"), bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
        
        search_ent = tk.Entry(head, font=("Consolas", 10), bd=1, width=24) 
        search_ent.pack(side=tk.LEFT, padx=2, ipady=6)
        
        btn_nav_opts = {"font": ("Arial", 9, "bold"), "bg": "#dcdde1", "relief": tk.GROOVE, "padx": 12, "pady": 4}
        
        # 文本框
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=self.ui_font, bg="white", 
                                               undo=True, spacing1=self.line_spacing, spacing3=self.line_spacing)

        btn_up = tk.Button(head, text="↑", command=lambda: self.do_search(search_ent.get(), text_widget, cfg, direction="prev"), **btn_nav_opts)
        btn_up.pack(side=tk.LEFT, padx=1)
        btn_down = tk.Button(head, text="↓", command=lambda: self.do_search(search_ent.get(), text_widget, cfg, direction="next"), **btn_nav_opts)
        btn_down.pack(side=tk.LEFT, padx=1)

        # 绑定回车搜索
        search_ent.bind("<Return>", lambda e: self.do_search(search_ent.get(), text_widget, cfg, direction="next"))

        # [右侧固定元素]
        if cfg["is_orig"]:
            tk.Button(head, text="💾保存", bg="#3498db", fg="white", font=("Consolas", 10, "bold"), relief=tk.FLAT, padx=10,
                      command=lambda: self.save_to_disk(cfg["path_var"].get(), text_widget)).pack(side=tk.RIGHT, padx=5)
            text_widget.tag_configure("highlight", background="#ffeaa7", foreground="#d63031")
            if cfg["is_main"]: self.text_orig_main = text_widget
            else: self.text_orig_comp = text_widget
        else:
            text_widget.bind("<Key>", lambda e: "break" if not (e.state & 4 and e.keysym.lower() in ('c', 'a')) else None)
            if cfg["is_main"]: 
                self.text_extra_main = text_widget
                text_widget.bind("<Button-1>", lambda e: self.on_result_click(e, self.text_extra_main, self.text_orig_main, is_main=True))
            else: 
                self.text_extra_comp = text_widget
                text_widget.bind("<Button-1>", lambda e: self.on_result_click(e, self.text_extra_comp, self.text_orig_comp, is_main=False))

        # [中间拖拽句柄] - 只有这个空白区域可拖动
        drag_handle = tk.Frame(head, bg="#ecf0f1", cursor="fleur")
        drag_handle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        drag_handle.bind("<Button-1>", lambda e: self.on_drag_start(e, frame))
        drag_handle.bind("<ButtonRelease-1>", lambda e: self.on_drag_release(e, frame))

        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.tag_configure("find", background="#7bed9f", borderwidth=1, relief="solid")
        
        frame.text_widget = text_widget
        return frame

    def on_drag_start(self, event, frame):
        frame.drag_start_x = event.x_root
        frame.config(highlightbackground="#e67e22", highlightthickness=2)

    def on_drag_release(self, event, frame):
        frame.config(highlightthickness=0)
        delta = event.x_root - frame.drag_start_x
        if abs(delta) < 40: return
        current_idx = self.columns.index(frame)
        shift = int(delta / (frame.winfo_width() / 1.5))
        target_idx = max(0, min(len(self.columns) - 1, current_idx + shift))
        if target_idx != current_idx:
            self.columns.pop(current_idx)
            self.columns.insert(target_idx, frame)
            for col in self.columns: self.workspace.forget(col)
            for col in self.columns: self.workspace.add(col, stretch="always")

    def display_extras(self, widget, extras):
        widget.delete(1.0, tk.END)
        wid = str(widget)
        for i, b in enumerate(extras):
            tag = f"block_{i}"
            del_tag = f"del_{i}"
            color = self.palette[i % len(self.palette)]
            widget.insert(tk.END, " [❌ 删除此块] \n", del_tag)
            widget.tag_configure(del_tag, background=color, foreground="red", justify='right', font=("Consolas", 10, "bold"))
            widget.insert(tk.END, b['content'] + "\n", tag)
            widget.tag_configure(tag, background=color, spacing1=self.line_spacing, spacing3=self.line_spacing)
            widget.tag_bind(del_tag, "<Button-1>", lambda e, w=widget, t=tag, dt=del_tag: self.delete_block(w, t, dt))
            widget.tag_bind(del_tag, "<Enter>", lambda e, w=widget: w.config(cursor="hand2"))
            widget.tag_bind(del_tag, "<Leave>", lambda e, w=widget: w.config(cursor="arrow"))
            self.tag_metadata[f"{wid}_{tag}"] = (b['line_start'], b['line_count'])
            widget.tag_bind(tag, "<Enter>", lambda e, w=widget: w.config(cursor="hand2"))
            widget.tag_bind(tag, "<Leave>", lambda e, w=widget: w.config(cursor="arrow"))

    def delete_block(self, widget, block_tag, del_tag):
        ranges = widget.tag_ranges(block_tag)
        del_ranges = widget.tag_ranges(del_tag)
        if ranges and del_ranges:
            widget.delete(del_ranges[0], ranges[1])

    def do_search(self, query, widget, cfg, direction="next"):
        if not query: return
        widget.tag_remove("find", "1.0", tk.END)
        wid = str(widget)
        if wid not in self.search_indices: self.search_indices[wid] = "1.0"
        start_pos = self.search_indices[wid]
        
        if direction == "next":
            pos = widget.search(query, start_pos, stopindex=tk.END)
            if not pos: pos = widget.search(query, "1.0", stopindex=tk.END)
        else:
            pos = widget.search(query, start_pos, stopindex="1.0", backwards=True)
            if not pos: pos = widget.search(query, tk.END, stopindex="1.0", backwards=True)
        
        if pos:
            # 记录搜索词高亮
            end_pos = f"{pos}+{len(query)}c"
            widget.tag_add("find", pos, end_pos)
            self.search_indices[wid] = end_pos if direction == "next" else pos
            
            # --- 自动定位代码块逻辑 ---
            if not cfg["is_orig"]:
                # 结果区：找到关键词所属的 block 标签
                tags = widget.tag_names(pos)
                for t in tags:
                    if t.startswith("block_"):
                        # 模拟点击该块执行定位
                        target_orig = self.text_orig_main if cfg["is_main"] else self.text_orig_comp
                        self.on_block_locate(widget, t, target_orig, cfg["is_main"])
                        widget.see(pos) # 确保结果区也滚动到此处
                        break
            else:
                # 原文件区：向上查找 Show/Hide 行
                block_start_pos = widget.search(r'^(Show|Hide)\b', pos, stopindex="1.0", backwards=True, regexp=True)
                if block_start_pos:
                    # 向下查找下一个 Show/Hide 作为结尾
                    block_end_pos = widget.search(r'^(Show|Hide)\b', f"{block_start_pos} lineend", stopindex=tk.END, regexp=True)
                    if not block_end_pos: block_end_pos = tk.END
                    
                    widget.tag_remove("highlight", "1.0", tk.END)
                    widget.tag_add("highlight", block_start_pos, block_end_pos)
                    widget.see(block_start_pos)
                    # 更新当前定位状态，方便 BaseType 替换
                    line_start = int(block_start_pos.split('.')[0])
                    # 粗略计算行数用于替换
                    line_end = int(widget.index(block_end_pos).split('.')[0]) if block_end_pos != tk.END else int(widget.index(tk.END).split('.')[0])
                    if cfg["is_main"]: self.current_main_locate = (line_start, line_end - line_start)
                    else: self.current_comp_locate = (line_start, line_end - line_start)
        else:
            messagebox.showinfo("搜索", "未找到匹配项")

    def on_result_click(self, event, widget, target_orig, is_main):
        idx = widget.index(f"@{event.x},{event.y}")
        tags = widget.tag_names(idx)
        for t in tags:
            if t.startswith("block_"):
                self.on_block_locate(widget, t, target_orig, is_main)
                break

    def on_block_locate(self, widget, tag, target_orig, is_main):
        wid = str(widget)
        key = f"{wid}_{tag}"
        if key in self.tag_metadata:
            l_s, l_c = self.tag_metadata[key]
            target_orig.tag_remove("highlight", "1.0", tk.END)
            s_p, e_p = f"{l_s}.0", f"{l_s + l_c}.0"
            target_orig.tag_add("highlight", s_p, e_p)
            target_orig.see(s_p)
            if is_main: self.current_main_locate = (l_s, l_c)
            else: self.current_comp_locate = (l_s, l_c)
            target_orig.focus_set()

    def browse_file(self, var):
        filename = filedialog.askopenfilename(filetypes=[("过滤器", "*.filter"), ("所有文件", "*.*")])
        if filename: var.set(filename)

    def save_to_disk(self, path, widget):
        if not path: return
        try:
            content = widget.get(1.0, tk.END)
            with open(path, 'w', encoding='utf-8') as f: f.write(content)
            messagebox.showinfo("成功", "保存成功")
        except Exception as e: messagebox.showerror("错误", str(e))

    def get_comparison_key(self, line):
        return re.sub(r'^(Show|Hide)\b', '', line, flags=re.IGNORECASE).strip()

    def parse_blocks(self, filepath, text_widget):
        blocks = []
        try:
            with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f: content = f.read()
            text_widget.delete(1.0, tk.END); text_widget.insert(tk.END, content)
            lines = content.splitlines()
            cur_b, cur_h, s_line = [], None, 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.lower().startswith("show") or stripped.lower().startswith("hide"):
                    if cur_h is not None:
                        blocks.append({'key': self.get_comparison_key(cur_h), 'content': "\n".join(cur_b) + "\n", 'line_start': s_line + 1, 'line_count': len(cur_b)})
                    cur_h, cur_b, s_line = stripped, [line], i
                else:
                    if cur_h is not None: cur_b.append(line)
            if cur_h is not None:
                blocks.append({'key': self.get_comparison_key(cur_h), 'content': "\n".join(cur_b) + "\n", 'line_start': s_line + 1, 'line_count': len(cur_b)})
        except Exception as e: messagebox.showerror("错误", str(e))
        return blocks

    def run_comparison(self):
        p1, p2 = self.main_file_path.get(), self.comp_file_path.get()
        if not p1 or not p2: return
        self.tag_metadata = {}
        b1 = self.parse_blocks(p1, self.text_orig_main)
        b2 = self.parse_blocks(p2, self.text_orig_comp)
        t2 = list(b2); ex1, ex2 = [], []
        for item in b1:
            idx = -1
            for i, target in enumerate(t2):
                if item['key'] == target['key']: idx = i; break
            if idx != -1: t2.pop(idx)
            else: ex1.append(item)
        ex2 = t2
        self.display_extras(self.text_extra_main, ex1)
        self.display_extras(self.text_extra_comp, ex2)

    def replace_basetype_logic(self):
        if not self.current_main_locate or not self.current_comp_locate:
            return messagebox.showwarning("提示", "请先在结果区点击块或通过搜索定位代码块。")
        try:
            c_s, c_cnt = self.current_comp_locate
            comp_block = self.text_orig_comp.get(f"{c_s}.0", f"{c_s + c_cnt}.0")
            bt_line = None
            for line in comp_block.splitlines():
                if "BaseType" in line: bt_line = line; break
            if not bt_line: return
            m_s, m_cnt = self.current_main_locate
            main_lines = self.text_orig_main.get(f"{m_s}.0", f"{m_s + m_cnt}.0").splitlines()
            new_l, replaced = [], False
            for line in main_lines:
                if "BaseType" in line: new_l.append(bt_line); replaced = True
                else: new_l.append(line)
            if replaced:
                self.text_orig_main.delete(f"{m_s}.0", f"{m_s + m_cnt}.0")
                self.text_orig_main.insert(f"{m_s}.0", "\n".join(new_l) + "\n")
                self.text_orig_main.tag_add("highlight", f"{m_s}.0", f"{m_s + m_cnt}.0")
        except Exception as e: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = FilterComparatorApp(root)
    root.mainloop()
