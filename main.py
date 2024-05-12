import os
# os.environ["KIVY_AUDIO"] = "ffpyplayer"
os.environ["KIVY_AUDIO"] = "android"
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.lang import Builder
from util import bili_download,list_files_in_directory
# from kivymd.app import MDApp
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.recycleview import RecycleView
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
import time
import random
from kivy.utils import platform
import logging
'''
爬B站视频，然后下载对应音频，进行播放

界面设计（必要功能）：
按钮<下载音频>
按钮<列表管理>
按钮<播放> ->  进入界面（罗列全部音频名）
按钮<播放方式> （单曲循环or列表训练or随机）

可增加功能：封面，建立歌单分组 ，歌词
'''

# 引入资源目录,如res目录位于项目根目录下，写相对路径(不要写绝对路径)相当于告诉kivy　DroidSansFallback.ttf 字体位于res目录中
from kivy.resources import resource_add_path, resource_find
resource_add_path(".")
# 替换kivy中的默认字体，使用我们的新字体
from kivy.core.text import LabelBase
LabelBase.register('Roboto', 'WeiRuanYaHei.ttf')

PATH = os.path.abspath("./mp3downloadCC/")
# if platform == 'android':
#     from android.permissions import request_permissions, Permission,check_permission
#     while not check_permission('android.permission.WRITE_EXTERNAL_STORAGE') and not check_permission('android.permission.WRITE_EXTERNAL_STORAGE'):
#         request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
#     logging.info(f"写权限检查：{check_permission('android.permission.WRITE_EXTERNAL_STORAGE')}")
#     logging.info(f"读权限检查：{check_permission('android.permission.READ_EXTERNAL_STORAGE')}")
#
#     # 获取外部存储路径
#     storage_path = storagepath.get_external_storage_dir()
#     # storage_path = App.get_running_app().user_data_dir
#     # 创建 'mp3download' 文件夹
#     mp3download_dir = os.path.join(storage_path, 'mp3downloadCC')
#     # os.makedirs(mp3download_dir, exist_ok=True)
#     PATH = mp3download_dir

IS_EDIT = False
show_name_list = [] #和delete_name_list共同控制删除时的选中
delete_name_list = []
# print(show_name_list)
ClickableLabel_Refresh = 0
# 播放列表
Order_Play_List = []
Random_Play_List = []
Sound_Cuurent_Play = None
Audio_Pos = -1
Play_Index = -1
Is_Loop = False
Play_Mode = 1  # 1：列表循环（默认）2：单曲循环，3：随机循环
Is_Stop_Manually = False
Last_Path = None

default_download_text = '在此输入b站视频链接\n如果是小程序，请复制视频号'
default_part_text = "在此输入要下载的分p号（视频未分p请忽略）"
default_title_text = "在此输入想另取的标题（没有请忽略）"

default_error_text = "下载出错，请检查后重试"
default_empty_error_text = "网址为空，请重新输入"
default_part_error_text = '分p号只能为数字，请重新输入'
default_text = [default_download_text,default_part_text,default_title_text]
default_error = [default_error_text,default_empty_error_text,default_part_error_text]
class PlaceholderTextInput(TextInput):
    def __init__(self, text_type,**kwargs):
        super().__init__(**kwargs)
        self.foreground_color = (0.5, 0.5, 0.5, 1)  # 设置默认的字体颜色为灰色
        self.bind(focus=self.on_focus)
        self.text_type = text_type
    def on_focus(self, instance, value):
        if value:  # 当输入框获取焦点
            if self.text == default_text[self.text_type] or self.text in default_error:  # 如果文本是默认文本
                self.text = ''  # 清空输入框
                self.foreground_color = (0, 0, 0, 1)  # 设置字体颜色为黑色
        else:  # 当输入框失去焦点
            if self.text == '':  # 如果输入框为空
                self.text = default_text[self.text_type]  # 设置默认文本
                self.foreground_color = (0.5,0.5,0.5,1) # 设置字体颜色为灰色
Builder.load_string('''
<RV>:
    viewclass: 'ClickableLabel'
    RecycleBoxLayout:
        default_size: None, root.height / 11
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        spacing: root.height / 80  # 添加这一行
''')
Builder.load_string('''
<ClickableLabel>:
    size_hint_y: 0.15
    canvas.before:
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Rectangle:
            pos: self.pos
            size: self.size
''')
class ClickableLabel(Label):  # a song
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = [0, 0, 0, 1]  # 设置字体颜色为黑色
        # self.is_edit = False
        self.audio_pos = 0
        self.is_selected = False
        self.bind(text=self.refresh_view)

    def on_touch_up(self, touch):
        global IS_EDIT
        global show_name_list
        global Sound_Cuurent_Play
        global Audio_Pos
        global Play_Index
        global Random_Play_List
        global Order_Play_List
        global Is_Stop_Manually
        global Play_Mode,Last_Path,delete_name_list
        # print(IS_EDIT)
        if self.collide_point(*touch.pos):
            # print(f"点击到了{self.text}")
            if IS_EDIT is False:
                # 调用 播放
                if Sound_Cuurent_Play:
                    logging.info("1start")
                    if Sound_Cuurent_Play.state == 'play':
                        logging.info("1.1start")
                        # 存在且在播
                        if Sound_Cuurent_Play.source == self.path:
                            logging.info("1.1.1start")
                            # 在播的是同一首，就暂停
                            Audio_Pos = Sound_Cuurent_Play.get_pos()
                            Is_Stop_Manually = True
                            Sound_Cuurent_Play.stop()
                            self.color = [0, 0, 0, 1]
                            logging.info("1.1.1end")
                        else:
                            # 在播的不是同一首
                            logging.info("1.1.2start")
                            Last_Path = Sound_Cuurent_Play.source
                            Is_Stop_Manually = True
                            Sound_Cuurent_Play.stop()
                            # Sound_Cuurent_Play.unload()
                            # del Sound_Cuurent_Play
                            Sound_Cuurent_Play = SoundLoader.load(self.path)
                            Play_Index = Order_Play_List.index(self.text) if Play_Mode!=3 else Random_Play_List.index(self.text)
                            Sound_Cuurent_Play.bind(on_stop=play2stop)
                            Sound_Cuurent_Play.loop = Is_Loop
                            Sound_Cuurent_Play.play()
                            self.color = [0, 0, 1, 1]
                            logging.info("1.1.2end")
                        return False
                    elif Sound_Cuurent_Play.state == 'stop':
                        # 存在但不在播， 比如同一首的暂停和不同首的暂停
                        logging.info("1.2start")
                        if Sound_Cuurent_Play.source == self.path:
                            logging.info("1.2.1start")
                            # 是同一首的暂停，那就继续播
                            Sound_Cuurent_Play.play()
                            time.sleep(0.01)
                            Sound_Cuurent_Play.seek(Audio_Pos)
                            Audio_Pos = 0
                            self.color = [0, 0, 1, 1]
                            logging.info("1.2.1end")

                        else:
                            # 是另一首歌的暂停，点了这一首
                            logging.info("1.2.2start")
                            Last_Path = Sound_Cuurent_Play.source
                            Is_Stop_Manually = True
                            Sound_Cuurent_Play.stop()
                            Sound_Cuurent_Play.unload()
                            Sound_Cuurent_Play = SoundLoader.load(self.path)
                            Play_Index = Order_Play_List.index(self.text) if Play_Mode != 3 else Random_Play_List.index(self.text)
                            Sound_Cuurent_Play.bind(on_stop=play2stop)
                            Sound_Cuurent_Play.loop = Is_Loop
                            Sound_Cuurent_Play.play()
                            self.color = [0, 0, 1, 1]
                            logging.info("1.2.2end")
                        return False
                else:
                    logging.info("2start")
                    # 如果不存在，那就播这一首
                    Sound_Cuurent_Play = SoundLoader.load(self.path)
                    Play_Index = Order_Play_List.index(self.text) if Play_Mode == 1 else Random_Play_List.index(self.text)
                    Sound_Cuurent_Play.bind(on_stop=play2stop)
                    Sound_Cuurent_Play.loop = Is_Loop
                    Sound_Cuurent_Play.play()
                    self.color = [0, 0, 1, 1]
                    logging.info("2end")
                return False
            else:
                # 编辑模式
                if self.is_selected is False:
                    # 增加可读性，就这么写吧
                    # print(self.text)
                    delete_name_list.insert(0,self.text)
                    # print("show_name_list:",show_name_list)
                    self.color = [1, 0, 0, 1]
                    self.is_selected = True
                else:
                    # show_name_list.insert(0,self.text)
                    delete_name_list.remove(self.text) if self.text in delete_name_list else None
                    self.color = [0, 0, 0, 1]
                    self.is_selected = False
                return False
        else:
            if Sound_Cuurent_Play:
                # print(f"未点击{self.text}，self.path:{self.path},当前path{Sound_Cuurent_Play.source}")
                # 这里有一个bug，点了song1后点song2， 会有2种情况，song1在song2前处理和后处理，如果是前处理，就没有任何有效信息，让我把song1的蓝标签改黑
                # if Last_Path:
                    # if self.path==Last_Path:
                # if self.path != Sound_Cuurent_Play.source:
                self.color = [0, 0, 0, 1]
            if self.color == [1, 0, 0, 1] and IS_EDIT is False:
                self.color = [0, 0, 0, 1]
                self.audio_pos = 0
                self.is_selected = False
        return False

    def refresh_view(self, instance, value):
        global Sound_Cuurent_Play
        # if self.color == [1, 0, 0, 1] and IS_EDIT == False:
        if self.color == [1, 0, 0, 1] and self.is_selected==True:
            self.color = [0, 0, 0, 1]
            self.audio_pos = 0
            self.is_selected = False
        if Sound_Cuurent_Play:
            if os.path.join(PATH,self.text+".m4a") == Sound_Cuurent_Play.source and Sound_Cuurent_Play.state=='play':
                self.color = [0, 0, 1, 1]
            else:
                self.color = [0, 0, 0, 1]

def refresh_Play_List():
    global Random_Play_List
    global Order_Play_List
    global show_name_list
    show_name_list = list_files_in_directory(PATH)
    Random_Play_List = show_name_list
    Order_Play_List = show_name_list
    random.shuffle(Random_Play_List)
class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)
        self.data = [{"text": x, 'path':os.path.join(PATH,x+".m4a")} for x in show_name_list]  # 把每一个文件放在一个字典中

def download_mp3(b):
    box1 = BoxLayout(orientation='vertical')

    input_path = PlaceholderTextInput(text=default_download_text,text_type=0,size_hint=(1, 0.2), pos_hint={'center_x': 0.5, 'y': 0.77})  # 创建文本输入框
    input_part = PlaceholderTextInput(text=default_part_text,text_type=1,input_type='number',size_hint=(1, 0.12), pos_hint={'center_x': 0.5, 'y': 0.5})  # 视频分p输入框
    input_title = PlaceholderTextInput(text=default_title_text,text_type=2,size_hint=(1, 0.12), pos_hint={'center_x': 0.5, '_y': 0.35})  # 自行取标题输入

    box11 = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), pos_hint={'center_x': 0.5, 'y': 0.1})

    cancel_button = Button(text='取消', size_hint=(0.4, 1), pos_hint={'center_x': 0.3, 'center_y': 0.5})  # 创建"取消"按钮
    confirm_button = Button(text='下载', size_hint=(0.4, 1), pos_hint={'center_x': 0.7, 'center_y': 0.5})  # 创建"确定"按钮
    box11.add_widget(cancel_button)
    box11.add_widget(confirm_button)

    box1.add_widget(input_path)
    box1.add_widget(Widget(size_hint=(1, 0.02)))
    box1.add_widget(input_part)
    box1.add_widget(Widget(size_hint=(1, 0.02)))
    box1.add_widget(input_title)
    box1.add_widget(Widget(size_hint=(1, 0.02)))
    box1.add_widget(box11)

    popup = Popup(title='', content=box1, size_hint=(0.87, 0.5), pos_hint={'center_x': 0.5, 'y': 0.48})
    cancel_button.bind(on_release=popup.dismiss)  # 绑定"取消"按钮的dismiss事件
    def download_confirm(instance):
        info = {'code':-1,'title':None}
        if input_path.text == default_text[0] or input_path.text == default_empty_error_text or input_path.text==default_error_text:
            input_path.text = default_empty_error_text
            input_path.foreground_color = "FF0000"
            return
        if input_part.text != default_part_text and input_part.text.isdigit() is False:
            input_part.text = default_part_error_text
            input_part.foreground_color = "FF0000"
            return
        try:
            info = bili_download(Path=input_path.text,part_num=input_part.text,title=input_title.text,download_location=PATH)
        except:
            # popup_error = Popup(title='下载失败',
            #               content=Label(text='若有vpn请关闭\n（点击其他任意处关闭）'),
            #               size_hint=(None, None), size=(400, 400), auto_dismiss=True)
            # popup_error.open()
            input_path.text = default_error_text
            input_path.foreground_color = "FF0000"
        if info['code'] == -1:
            # 下载失败 ， 清空
            input_path.text = default_error_text
            input_path.foreground_color = "FF0000"
        elif info['code'] == 1:
            # 下载成功
            # 这里应该有个提示，后续再弄
            close_btn = Button(text='确定',size_hint=(0.3, 0.4),pos_hint={'center_x': 0.5, 'y': 0.25})
            popup2 = Popup(title=f'{info["title"]}\n搜索成功，下载完成！', content=close_btn, size_hint=(0.65, 0.3),pos_hint={'center_x': 0.5, 'y': 0.6},auto_dismiss=True)
            popup2.open()

            # close_btn.bind(on_release=popup.dismiss)
            close_btn.bind(on_release=popup2.dismiss)

        refresh_Play_List()

    confirm_button.bind(on_release=download_confirm)
    popup.open()  # 打开弹出窗口

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        # self.add_widget(Button(text='到第二个界面', on_release=self.change_screen))
        # layout1 = BoxLayout(orientation='horizontal', size_hint=(0.8, None), height=50, pos_hint={'center_x': 0.5, 'y': 0.8})
        btn_download = Button(text='下载音频',size_hint=(0.3, 0.1), pos_hint={'center_x': 0.25, 'y': 0.8})
        btn_download.bind(on_release=download_mp3)
        btn_list_manage = Button(text='列表管理',size_hint=(0.3, 0.1), pos_hint={'center_x': 0.75, 'y': 0.8})
        btn_list_manage.bind(on_release=self.to_manage_screen)
        # layout1.add_widget(button)
        # layout1.add_widget(button2)
        # self.add_widget(layout1)
        self.add_widget(btn_download)
        self.add_widget(btn_list_manage)

        self.btn_random_play = Button(text='随机开始一首',size_hint=(0.8, 0.2),pos_hint={'center_x': 0.5, 'y': 0.3})
        self.btn_random_play.bind(on_release=self.random_play)
        self.add_widget(self.btn_random_play)

        self.btn_check_song = Button(text='查看当前曲目', size_hint=(0.7, 0.15),pos_hint={'center_x': 0.5, 'y': 0.5},background_color=[1,1,1,0.4])
        self.btn_check_song.bind(on_release=self.check_song)
        self.add_widget(self.btn_check_song)

        self.btn_play_last = Button(text='上一首',size_hint=(0.8, 1))
        self.btn_play_last.bind(on_release=self.play_last)
        self.btn_pause = Button(text='暂停/播放',size_hint=(1.3, 1))
        self.btn_pause.bind(on_release=self.play_pause)
        self.btn_play_next = Button(text='下一首',size_hint=(0.8, 1))
        self.btn_play_next.bind(on_release=self.play_next)
        self.btn_play_mode = Button(text='列表循环',size_hint=(0.2, 0.08),pos_hint={'center_x': 0.7, 'y': 0.1})

        self.btn_play_mode.bind(on_release=self.play_mode_change)
        layout2 = BoxLayout(orientation='horizontal', size_hint=(0.8, 0.06), pos_hint={'center_x': 0.5, 'y': 0.2})
        layout2.add_widget(self.btn_play_last)
        layout2.add_widget(self.btn_pause)
        layout2.add_widget(self.btn_play_next)
        self.add_widget(self.btn_play_mode)
        self.add_widget(layout2)

        self.btn_info = Button(text='注意事项', size_hint=(0.2, 0.06),pos_hint={'center_x': 0.3, 'y': 0.1},background_color=[1,1,1,0.3])
        self.btn_info.bind(on_release=self.show_info)
        self.add_widget(self.btn_info)
    def show_info(self,btn):
        label = Label(text='罗列bug和解决方法：\n'
                             '1.下载多p的视频时，第一p的视频标题不是该p标题，而是视频标题\n'
                             '  解决：下载前点一下第一p，再复制网页地址\n'
                             '2.删除后仍出现红字：\n'
                             '  解决：点击刷新or重新打开软件\n (已修复)'
                             '3.开着vpn下载会报错，关闭后再下载\n'
                             '4.吃内存。项目用的kivy框架有点问题，每次播放都会吃一首歌的内存\n'
                             '  解决：用一段时间后关闭app即可\n'
                             '5.暂停/播放按钮不对劲\n'
                             '  解决：只是显示不对劲，功能正常\n',
                        size_hint=(1, None))
        # label.height = label.texture_size[1]
        label.bind(texture_size=label.setter('size'))
        def update_text_size(*args):
            label.text_size = (label.width, None)
        label.bind(width=update_text_size)

        scroll = ScrollView(size_hint=(1, 0.95),pos_hint={'center_x': 0.5, 'center_y': 0.5})
        scroll.add_widget(label)
        popup = Popup(title='注意事项',
                      content=scroll,
                      size_hint=(0.7, 0.7),pos_hint={'center_x': 0.5, 'center_y': 0.5},auto_dismiss=True)
        popup.open()

    def check_song(self,btn):
        global Sound_Cuurent_Play,Order_Play_List,Random_Play_List,Play_Index,Play_Mode
        if not Sound_Cuurent_Play:
            self.btn_check_song.text = '当前并未播放噢\n刷新'
        else:
            title = os.path.basename(Sound_Cuurent_Play.source)
            title = os.path.splitext(title)[0]
            self.btn_check_song.text = f'{title}\n刷新'
    def play_pause(self,btn):
        # 暂停按钮
        global Audio_Pos
        global Sound_Cuurent_Play
        global Is_Stop_Manually
        if not Sound_Cuurent_Play or Play_Index == -1:
            pass
        else:
            if Sound_Cuurent_Play:
                if Sound_Cuurent_Play.state == 'play':
                    Audio_Pos = Sound_Cuurent_Play.get_pos()
                    Is_Stop_Manually = True
                    Sound_Cuurent_Play.stop()
                    self.btn_pause.text = '继续'

                elif Sound_Cuurent_Play.state == 'stop':
                    Sound_Cuurent_Play.play()
                    time.sleep(0.01)
                    Sound_Cuurent_Play.seek(Audio_Pos)
                    Audio_Pos = 0
                    self.btn_pause.text = '暂停'
    def play_last(self,btn):
        global Is_Stop_Manually, Sound_Cuurent_Play, Play_Mode, Play_Index, Is_Loop
        global Order_Play_List,Random_Play_List
        if not Sound_Cuurent_Play or Play_Index == -1:
            pass
        else:
            self.btn_check_song.text = '查看当前曲目'
            # 手动停止当前歌
            Is_Stop_Manually = True
            Sound_Cuurent_Play.stop()
            Play_Index = Play_Index - 1 if Play_Index-1 >= 0 else len(Order_Play_List)-1
            if Play_Mode == 1 or Play_Mode == 2:
                Sound_Cuurent_Play = SoundLoader.load(os.path.join(PATH, Order_Play_List[Play_Index]+'.m4a'))
            elif Play_Mode == 3:
                Sound_Cuurent_Play = SoundLoader.load(os.path.join(PATH, Random_Play_List[Play_Index]+'.m4a'))
            Sound_Cuurent_Play.bind(on_stop=play2stop)
            Sound_Cuurent_Play.loop = Is_Loop
            Sound_Cuurent_Play.play()
    def play_next(self,btn):
        global Is_Stop_Manually, Sound_Cuurent_Play, Play_Mode, Play_Index, Is_Loop
        global Order_Play_List,Random_Play_List
        if not Sound_Cuurent_Play or Play_Index == -1:
            pass
        else:
            self.btn_check_song.text = '查看当前曲目'
            # 手动停止当前歌
            Is_Stop_Manually = True
            Sound_Cuurent_Play.stop()
            Play_Index = Play_Index + 1 if Play_Index+1 < len(Order_Play_List) else 0
            # print(Play_Index,Play_Mode,Order_Play_List)
            if Play_Mode == 1 or Play_Mode == 2:
                Sound_Cuurent_Play = SoundLoader.load(os.path.join(PATH, Order_Play_List[Play_Index]+'.m4a'))
            elif Play_Mode == 3:
                Sound_Cuurent_Play = SoundLoader.load(os.path.join(PATH, Random_Play_List[Play_Index]+'.m4a'))
            Sound_Cuurent_Play.bind(on_stop=play2stop)
            Sound_Cuurent_Play.loop = Is_Loop
            Sound_Cuurent_Play.play()
    def play_mode_change(self,btn):
        global Is_Loop
        global Play_Mode
        # 3种模式：单曲循环，随机循环，列表循环（默认）
        if Play_Mode == 1:
            self.btn_play_mode.text = '单曲循环'
            Is_Loop = True
            Play_Mode = 2
        elif Play_Mode == 2:
            self.btn_play_mode.text = '随机循环'
            Is_Loop = False
            Play_Mode = 3
        elif Play_Mode == 3:
            self.btn_play_mode.text = '列表循环'
            Is_Loop = False
            Play_Mode = 1

    def random_play(self,btn):
        global Play_Index
        # 初始化Play_list
        # 业务逻辑： 建立歌单，len里随机一个数，开始播放
        global show_name_list
        if not show_name_list:
            popup = Popup(title='失败',
                          content=Label(text='列表为空\n点击其他任意处关闭对话框'),
                          size_hint=(0.6, 0.5),pos_hint={'center_x': 0.5, 'center_y': 0.5}, auto_dismiss=True)
            popup.open()
        else:
            Play_Index = random.randrange(0, len(show_name_list))
            self.btn_check_song.text = '查看当前曲目'
            play_by_order()
    # 点击按钮后切换到第二个界面
    def to_manage_screen(self, btn):
        self.manager.transition = SlideTransition(direction='left')  # 从右边切换
        self.manager.current = 'mp3manage_screen'
def play_by_order():
    global Play_Index,Sound_Cuurent_Play,Order_Play_List,Random_Play_List,Is_Stop_Manually
    logging.info('play_by_order Start')
    if Play_Index >= len(Order_Play_List):
        Play_Index = 0
        random.shuffle(Random_Play_List)
    if Sound_Cuurent_Play:
        Is_Stop_Manually = True
        Sound_Cuurent_Play.stop()
    if Play_Mode == 1 or Play_Mode == 2:
        Sound_Cuurent_Play = SoundLoader.load(os.path.join(PATH, Order_Play_List[Play_Index]+'.m4a'))
    elif Play_Mode == 3:
        Sound_Cuurent_Play = SoundLoader.load(os.path.join(PATH,Random_Play_List[Play_Index]+'.m4a'))
    Sound_Cuurent_Play.bind(on_stop=play2stop)
    Sound_Cuurent_Play.loop = Is_Loop
    Sound_Cuurent_Play.play()
def play2stop(self):
    # 一首歌播放暂停后
    global Play_Index
    global Is_Stop_Manually
    logging.info('play2stop Start')
    if Is_Stop_Manually is False:
        Play_Index += 1
        play_by_order()
    Is_Stop_Manually = False


# 第二个界面, 列表管理界面
class ManageScreen(Screen):
    def __init__(self, **kwargs):
        super(ManageScreen, self).__init__(**kwargs)
        self.top_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.07), pos_hint={'x': 0, 'y': 0.9})
        self.btn_return = Button(text='返回', size_hint=(0.25, 1))
        self.btn_return.bind(on_release=self.back2main_screen)
        self.btn_refresh = Button(text='刷新', size_hint=(0.25, 1))
        self.btn_refresh.bind(on_release=self.refresh)
        self.btn_edit = Button(text='编辑', size_hint=(0.25, 1))
        self.btn_edit.bind(on_release=self.toEditMode)
        self.top_layout.add_widget(self.btn_return)
        self.top_layout.add_widget(self.btn_refresh)
        self.top_layout.add_widget(Widget(size_hint=(0.25, 1)))  # 中间块
        self.top_layout.add_widget(self.btn_edit)

        # 下拉列表控件
        self.rv = RV(size_hint=(0.8, 0.9),pos_hint={'center_x': 0.5, 'y': 0.1})

        self.mid_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.7), pos_hint={'center_x': 0.5, 'y': 0.1})
        self.mid_layout.add_widget(self.rv)
        self.add_widget(self.top_layout)
        self.add_widget(self.mid_layout)

        # self.refresh(self.btn_refresh) # 手动刷新一下
    def toEditMode(self,instance):
        global IS_EDIT
        global show_name_list
        global Sound_Cuurent_Play
        # print("进入编辑")
        if self.btn_edit.text == '编辑':
            IS_EDIT = True
            self.btn_edit.text = '删除'
            self.btn_edit.background_color = [1, 0, 0, 1]
            self.btn_refresh.disabled = True

        else:
            # 执行删除
            try:
                if delete_name_list:
                    if Sound_Cuurent_Play:
                        Sound_Cuurent_Play.unload()
                    for delete_name in delete_name_list:
                        os.remove(os.path.join(PATH, delete_name+".m4a"))
                        if delete_name in show_name_list:
                            show_name_list.remove(delete_name)
            except Exception as e:
                print(e)
                popup = Popup(title='删除失败',
                              content=Label(text='有点bug，重新进入软件再删除\n点击其他任意处关闭对话框'),
                              size_hint=(0.6, 0.5), pos_hint={'center_x': 0.5, 'center_y': 0.5},auto_dismiss=True)
                popup.open()
            delete_name_list.clear()
            self.refresh(self.btn_refresh)
            refresh_Play_List()
            IS_EDIT = False
            self.btn_refresh.disabled = False
            self.btn_edit.text = '编辑'
            self.btn_edit.background_color=[1,1,1,1]

    def refresh(self, btn):
        global show_name_list
        # for child in self.mid_layout.children:
        #     if isinstance(child, RV):
        #         show_name_list = list_files_in_directory(PATH)
        #         child.data = [{"text": x, 'path': os.path.join(PATH, x+".m4a")} for x in show_name_list]  # 把每一个文件放在一个字典中
        #         child.refresh_from_data()
        #         # child.refresh_views()
        #         return True

        show_name_list = list_files_in_directory(PATH)
        self.rv.data.clear()
        self.rv.data = [{"text": x, 'path': os.path.join(PATH, x+".m4a")} for x in show_name_list]
        self.rv.refresh_from_data()
        return

    # 点击按钮后回到第一个界面
    def back2main_screen(self, btn):
        self.manager.transition = SlideTransition(direction='right')  # 从左边
        self.manager.current = 'main_screen'

class MyApp(App):
    def build(self):
        global PATH,show_name_list,Order_Play_List,Random_Play_List
        Window.clearcolor = (1, 1, 1, 1)
        if platform == 'android':
            storage_path = App.get_running_app().user_data_dir
            # 创建 'mp3download' 文件夹
            mp3download_dir = os.path.join(storage_path,'app' ,'mp3downloadCC')
            os.makedirs(mp3download_dir, exist_ok=True)
            PATH = mp3download_dir

        # 因为在移动端情况下，path需要先定义app再设置，而列表需要在PATH设置后设置
        show_name_list = list_files_in_directory(PATH)  # 和delete_name_list共同控制删除时的选中
        Order_Play_List = list(show_name_list)
        Random_Play_List = list(show_name_list)
        random.shuffle(Random_Play_List)

        sm = ScreenManager()
        # 添加两个界面到 ScreenManager
        sm.add_widget(MainScreen(name='main_screen'))
        sm.add_widget(ManageScreen(name='mp3manage_screen'))
        # 设置初始显示的界面
        sm.current = 'main_screen'
        return sm
    # def build(self):
    #     return Label(text='Hello World')


MyApp().run()