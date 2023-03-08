import sys  
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QProgressBar, QApplication
from PyQt6.QtCore import QThread, pyqtSignal
import searcher_ui
import os
import fnmatch
import string

#Я обещаю дописать комментарии....

#Класс, осуществляющий взаимодействие с интерфейсом и запускающий потоки
class Ffile(QtWidgets.QMainWindow, searcher_ui.Ui_mainWindow): #наследуется от Qt библиотеки для виджетов и файла с разметкой интерфейса
    def __init__(self):
        super().__init__()
        self.setupUi(self) 
        self.setWindowIcon(QtGui.QIcon('icon.png')) #подключение иконки 

        self.disks = self.get_disklist() #получение списка логических дисков

        #добавление чекбоксов на форму (каждый чекбокс - один диск)
        self.checkBoxes = dict()
        for d in self.disks:
            self.checkBoxes[d] = QtWidgets.QCheckBox(d)
            self.checkBoxes[d].setChecked(True)
            self.checkBoxes[d].stateChanged.connect(self.change_state_checkbox) # соединение события изменения чекбоксов с методом класса
            self.verticalLayout_2.addWidget(self.checkBoxes[d])

        #инициализация переменных:
        self.count_files = 0          # всего файлов
        self.found_files = list()     # найденных файлов
        self.current_count_files = 0  # текущего количества проверенных файлов
        self.thread_search = list()   # массив для потоков поиска файлов
        self.fund_files_text = ''     # найденные файлы в формате одной строки
        self.file_name = ''           # имя (маска) файла для поиска
        self.thread_analysis = list() # массив для потоков анализа количества файлов на дисках
        self.success_analysis = False # флаг об успешном анализе дисков: Trye - анализ закончен, False - анализ не закончен 

        # инициализация и запуск потоков анализа количества файлов (отдельно для каждого диска)
        for d in self.disks:
            self.thread_analysis.append(ThreadAnalysis(self, d))

        for th in self.thread_analysis:
            th.finished.connect(self.on_finished_analysis)
            th.start()

        self.pushButton.clicked.connect(self.searcher) # соединение события нажатия кнопки с методом класса, запускающим поиск

    # метод, запускающийся при изменении статусов чекбоксов
    def change_state_checkbox(self):
        for d in self.checkBoxes.keys():
            if not self.checkBoxes[d].isChecked():
                if self.disks.count(d) != 0:
                    self.disks.remove(d) # удаление локального диска из массива 
            else:
                if self.disks.count(d) == 0:
                    self.disks.append(d)  # добавление локального диска в массива 

    # метод, осуществляющий поиск файлов
    def searcher(self):
        #инициализируем и обновляем переменные
        s = self.lineEdit.text()                 
        self.textEdit.setText('')
        self.fund_files_text = ''
        self.found_files = list()
        self.label_3.setText('Найдено файлов: ')
        self.thread_search = list()
        self.current_count_files = 0
        self.file_name = s

        # выявление ошибок ввода
        if len(self.disks) == 0:
            self.textEdit.setText('Укажите диски для поиска!')
            return
        if len(s) == 0:
            self.textEdit.setText('Введите название (маску) файла!')
            return
        if s == '*' or s == '*.*':
            self.textEdit.setText('Укажите корректный запрос для поиска файлов!')
            return
        if len(s) > 255:
            self.textEdit.setText('Длина имени файла не может превышать 255 символов!')
            return
        if len(set(s) & set(['\\', '/', ':', '"', '<', '>', '|'])) > 0:
            self.textEdit.setText('Имя файла не должно содержать следующих знаков: \n \\ / : " < > |')
            return

        # деактивация кнопки поиска
        self.pushButton.setEnabled(False)

        #инициализация и запуск потоков поиска (отдельно для каждого диска)
        for d in self.disks:
            self.thread_search.append(ThreadSearch(self, d))

        for th in self.thread_search:
            th.progressed.connect(self.on_progress_search)
            th.finished.connect(self.on_finished_search)
            th.start()

    def on_finished_analysis(self):
        self.label_2.setText('Всего файлов: ' + str(self.count_files))
        self.sender().finished.disconnect(self.on_finished_analysis)
        self.thread_analysis.remove(self.sender())
        if len(self.thread_analysis) == 0:
            self.success_analysis = True

    def on_finished_search(self):
        self.sender().finished.disconnect(self.on_finished_search)
        self.sender().progressed.disconnect(self.on_progress_search)
        self.thread_search.remove(self.sender())
        self.label_3.setText('Найдено файлов: ' + str(len(self.found_files)))
        self.textEdit.setText(self.fund_files_text)
        if len(self.thread_search) == 0:
            self.pushButton.setEnabled(True)
            self.progressBar.setValue(100)

    def on_progress_search(self, value):
        if self.success_analysis:
            self.progressBar.setValue(int(self.current_count_files/self.count_files*100))
        else:
            self.progressBar.setValue(value)

    def get_disklist(self):
        disk_list = []
        for c in string.ascii_uppercase:
            disk = c+':'
            if os.path.isdir(disk):
                disk_list.append(disk + '/')
        return disk_list


#класс 
class ThreadAnalysis(QThread):

    def __init__(self, windowApp, disk, parent=None):
        super().__init__()
        self.windowApp = windowApp
        self.disk = disk

    def run(self):
        for rootdir, dirs, files in os.walk(self.disk):
            self.windowApp.count_files += len(files)


class ThreadSearch(QThread):
    progressed = pyqtSignal(int)

    def __init__(self, windowApp, disk, parent=None):
        super().__init__()
        self.windowApp = windowApp
        self.disk = disk

    def run(self):
        plug = 15 #заглушка для progressbar на случай если анализ количества файлов еще не был завершен 
        for rootdir, dirs, files in os.walk(self.disk):
            self.windowApp.current_count_files += len(files)
            self.progressed.emit(plug)
            for file in files:
                if fnmatch.fnmatch(file, self.windowApp.file_name):
                    self.windowApp.found_files.append(os.path.join(rootdir, file))
                    self.windowApp.fund_files_text = self.windowApp.fund_files_text + os.path.join(rootdir, file) + '\n\n'


def main():    
    app = QtWidgets.QApplication(sys.argv)  
    window = Ffile()
    
    file = open("MaterialDark.qss",'r')
    with file:
        qss = file.read()
        app.setStyleSheet(qss)
        
    window.show()       
    app.exec()  


if __name__ == '__main__':
    main()
