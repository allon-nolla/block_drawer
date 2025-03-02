import sys
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QMenu, QAction,
    QInputDialog, QMainWindow, QSplitter, QTableWidget, QTableWidgetItem,
    QGraphicsTextItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem,
    QMessageBox, QWidget, QVBoxLayout, QLabel, QSpinBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QObject
from PyQt5.QtGui import (
    QPen, QPainterPath, QBrush, QColor, QKeyEvent, QPainter
)

# --------------------- 端口配置对话框 ---------------------
class PortConfigDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        self.master_spin = QSpinBox()
        self.master_spin.setRange(0, 10)
        layout.addWidget(QLabel("Master数量:"))
        layout.addWidget(self.master_spin)

        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(0, 10)
        layout.addWidget(QLabel("Slave数量:"))
        layout.addWidget(self.slave_spin)

        self.bidir_spin = QSpinBox()
        self.bidir_spin.setRange(0, 10)
        layout.addWidget(QLabel("Bidirection数量:"))
        layout.addWidget(self.bidir_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setWindowTitle("端口配置")

    def get_values(self):
        return (
            self.master_spin.value(),
            self.slave_spin.value(),
            self.bidir_spin.value()
        )

# --------------------- 连接表格组件 ---------------------
class ConnectionTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["源节点", "源类型", "目标节点", "连接类型"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSortingEnabled(True)

    def update_connections(self, connections):
        self.clearContents()
        self.setRowCount(len(connections))
        for row, conn in enumerate(connections):
            self.setItem(row, 0, QTableWidgetItem(conn.start_node.text_item.toPlainText()))
            self.setItem(row, 1, QTableWidgetItem(conn.start_node.node_type))
            self.setItem(row, 2, QTableWidgetItem(conn.end_node.text_item.toPlainText()))
            self.setItem(row, 3, QTableWidgetItem(conn.label))

# --------------------- 连接线组件 ---------------------
class ConnectionLine(QGraphicsPathItem):
    def __init__(self, start_node, end_node, label=""):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.label = label
        self.setZValue(-1)
        self.setup_style()
        self.label_item = QGraphicsTextItem(label, self)
        self.update_path()

    def setup_style(self):
        self.setPen(QPen(Qt.darkGreen, 2, Qt.SolidLine, Qt.RoundCap))

    def update_path(self):
        path = QPainterPath()
        start_pos = self.start_node.sceneBoundingRect().center()
        end_pos = self.end_node.sceneBoundingRect().center()
        path.moveTo(start_pos)
        ctrl_point = (start_pos + end_pos) / 2 + QPointF(0, 50)
        path.quadTo(ctrl_point, end_pos)
        self.setPath(path)
        self.label_item.setPos(path.pointAtPercent(0.5))

# --------------------- 框图节点组件 ---------------------
class BlockNode(QGraphicsRectItem):
    NODE_TYPES = {
        "Function_IP": QColor(25, 25, 112),   # 深蓝色
        "Amba_bridge": QColor(50, 205, 50),    # 绿色
        "Comb_logic": QColor(147, 112, 219)    # 浅紫色
    }

    class NodeSignals(QObject):
        moved = pyqtSignal()
        type_changed = pyqtSignal(str)

    def __init__(self, text, x, y, node_type="Function_IP", master=0, slave=0, bidir=0):
        # 动态计算节点大小
        width = max(120, 30 * (max(master, slave) + 1))
        height = max(80, 30 * (bidir + 1))
        super().__init__(0, 0, width, height)
        
        self.connections = []
        self.signals = self.NodeSignals()
        self._node_type = node_type
        self.master_ports = master
        self.slave_ports = slave
        self.bidir_ports = bidir
        
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsScenePositionChanges)
        self.setPos(x, y)
        self.setBrush(QBrush(self.NODE_TYPES[self.node_type]))
        
        # 添加文本标签
        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setPos(10, self.rect().height()/2 - 15)
        
        # 创建端口
        self.create_ports()

    def create_ports(self):
        # Master端口（顶部）
        for i in range(self.master_ports):
            port = QGraphicsRectItem(0, 0, 25, 15, self)
            port.setBrush(QBrush(Qt.white))
            port.setPen(QPen(Qt.black, 1))
            x = (i + 1) * (self.rect().width() / (self.master_ports + 1)) - 12.5
            port.setPos(x, 2)
            label = QGraphicsTextItem(f"M{i+1}", port)
            label.setPos(2, -1)

        # Slave端口（底部）
        for i in range(self.slave_ports):
            port = QGraphicsRectItem(0, 0, 25, 15, self)
            port.setBrush(QBrush(Qt.white))
            port.setPen(QPen(Qt.black, 1))
            x = (i + 1) * (self.rect().width() / (self.slave_ports + 1)) - 12.5
            port.setPos(x, self.rect().height() - 17)
            label = QGraphicsTextItem(f"S{i+1}", port)
            label.setPos(2, -1)

        # Bidirection端口（左右）
        for i in range(self.bidir_ports):
            # 左侧
            port = QGraphicsRectItem(0, 0, 15, 25, self)
            port.setBrush(QBrush(Qt.white))
            port.setPen(QPen(Qt.black, 1))
            y = (i + 1) * (self.rect().height() / (self.bidir_ports + 1)) - 12.5
            port.setPos(2, y)
            label = QGraphicsTextItem(f"B{i+1}L", port)
            label.setPos(-10, 5)

            # 右侧
            port = QGraphicsRectItem(0, 0, 15, 25, self)
            port.setBrush(QBrush(Qt.white))
            port.setPen(QPen(Qt.black, 1))
            port.setPos(self.rect().width() - 17, y)
            label = QGraphicsTextItem(f"B{i+1}R", port)
            label.setPos(2, 5)

    @property
    def node_type(self):
        return self._node_type

    @node_type.setter
    def node_type(self, value):
        if value in self.NODE_TYPES:
            self._node_type = value
            self.setBrush(QBrush(self.NODE_TYPES[value]))
            self.signals.type_changed.emit(value)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.signals.moved.emit()
        elif change == QGraphicsItem.ItemPositionHasChanged:
            for conn in self.connections:
                conn.update_path()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        new_text, ok = QInputDialog.getText(None, "重命名节点", "新名称：", 
                                          text=self.text_item.toPlainText())
        if ok and new_text:
            self.text_item.setPlainText(new_text)
        super().mouseDoubleClickEvent(event)

# --------------------- 主绘图视图 ---------------------
class DiagramView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.nodes = []
        self.connections = []
        self.start_node = None
        self.context_menu_pos = QPointF()
        
        # 视图设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.init_context_menu()

    def init_context_menu(self):
        self.context_menu = QMenu()
        self.base_actions = [
            ("创建方框", self.create_block),
            ("删除选中项", self.delete_selected),
            ("创建连线", self.start_connection)
        ]

    def show_context_menu(self, pos):
        self.context_menu.clear()
        self.context_menu_pos = self.mapToScene(pos)
        
        # 动态添加右键菜单项
        selected_items = self.scene.selectedItems()
        if len(selected_items) == 1 and isinstance(selected_items[0], BlockNode):
            change_type_action = QAction("修改类型", self)
            change_type_action.triggered.connect(self.change_node_type)
            self.context_menu.addAction(change_type_action)
            
        for text, slot in self.base_actions:
            action = QAction(text, self)
            action.triggered.connect(slot)
            self.context_menu.addAction(action)
            
        self.context_menu.exec_(self.mapToGlobal(pos))

    def change_node_type(self):
        selected = self.scene.selectedItems()
        if not selected or not isinstance(selected[0], BlockNode):
            return
            
        node = selected[0]
        types = list(BlockNode.NODE_TYPES.keys())
        new_type, ok = QInputDialog.getItem(
            self, "修改类型", "选择节点类型：", 
            types, types.index(node.node_type), False
        )
        if ok and new_type:
            node.node_type = new_type

    def create_block(self):
        try:
            # 选择节点类型
            types = list(BlockNode.NODE_TYPES.keys())
            node_type, ok = QInputDialog.getItem(
                self, "选择类型", "请选择节点类型：", 
                types, 0, False
            )
            if not ok:
                return

            # 弹出端口配置对话框
            dialog = PortConfigDialog()
            if dialog.exec_() != QDialog.Accepted:
                return
            master, slave, bidir = dialog.get_values()

            position = self.context_menu_pos if not self.context_menu_pos.isNull() else QPointF(100, 100)
            new_block = BlockNode("新节点", position.x(), position.y(), 
                                node_type, master, slave, bidir)
            new_block.signals.moved.connect(self.update_connections)
            self.scene.addItem(new_block)
            self.nodes.append(new_block)
            new_block.setSelected(True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建节点失败：{str(e)}")

    def start_connection(self):
        selected = self.scene.selectedItems()
        if len(selected) == 1 and isinstance(selected[0], BlockNode):
            self.start_node = selected[0]
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            QMessageBox.warning(self, "提示", "请先选中一个起始节点")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragMode() == QGraphicsView.NoDrag:
            item = self.itemAt(event.pos())
            if isinstance(item, BlockNode) and self.start_node:
                self.create_connection(self.start_node, item)
                self.start_node = None
                self.setDragMode(QGraphicsView.RubberBandDrag)
        super().mousePressEvent(event)
   
    def create_connection(self, start_node, end_node):
        try:
            if start_node == end_node:
                QMessageBox.warning(self, "错误", "不能连接到自身")
                return
                
            if any(conn.start_node == start_node and conn.end_node == end_node 
                  for conn in self.connections):
                QMessageBox.warning(self, "提示", "连接已存在")
                return

            label, ok = QInputDialog.getText(self, "连线命名", "输入连接名称：")
            if ok:
                connection = ConnectionLine(start_node, end_node, label or "未命名")
                self.scene.addItem(connection)
                self.connections.append(connection)
                start_node.connections.append(connection)
                end_node.connections.append(connection)
                self.parent().connection_table.update_connections(self.connections)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建连接失败：{str(e)}")

    def delete_selected(self):
        try:
            selected = self.scene.selectedItems()
            for item in selected:
                if isinstance(item, BlockNode):
                    # 删除关联的连接线
                    for conn in item.connections[:]:
                        if conn in self.connections:
                            self.scene.removeItem(conn)
                            self.connections.remove(conn)
                            conn.start_node.connections.remove(conn)
                            conn.end_node.connections.remove(conn)
                    self.nodes.remove(item)
                elif isinstance(item, ConnectionLine):
                    item.start_node.connections.remove(item)
                    item.end_node.connections.remove(item)
                    self.connections.remove(item)
                self.scene.removeItem(item)
            self.parent().connection_table.update_connections(self.connections)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败：{str(e)}")

    def update_connections(self):
        for conn in self.connections:
            conn.update_path()

# --------------------- 主窗口 ---------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.diagram_view = DiagramView()
        self.connection_table = ConnectionTable()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("框图设计工具 v2.0")
        self.resize(1280, 720)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.diagram_view)
        splitter.addWidget(self.connection_table)
        splitter.setSizes([800, 400])
        self.setCentralWidget(splitter)
        
        self.setStyleSheet("""
            QGraphicsView { background: #F5F5F5; border-radius: 5px; }
            QTableWidget { font: 12pt 'Microsoft YaHei'; }
            QHeaderView::section { background: #4682B4; color: white; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
