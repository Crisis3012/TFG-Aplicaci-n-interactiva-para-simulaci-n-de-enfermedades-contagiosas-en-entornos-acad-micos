MAIN_STYLE = """
    QWidget {
        background-color: #2c2f33;
        color: white;
    }

    QLabel {
        color: white;
    }

    QPushButton {
        background-color: #7289da;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        padding: 8px;
    }

    QPushButton:hover {
        background-color: #5b6eae;
    }

    QPushButton:pressed {
        background-color: #4e5d94;
    }

    QLineEdit, QSpinBox, QComboBox {
        background-color: #f4f6f7;
        color: #1f2933;
        border-radius: 5px;
        padding: 4px;
    }

    QTreeWidget {
        background-color: #f4f6f7;
        color: white;
        border-radius: 5px;
        padding: 4px;
    }

    QTreeWidget::item:selected {
        background-color: #7289da;
        color: white;
    }

    QSlider {
        background-color: transparent;
    }
"""

LEFT_PANEL_STYLE = """
    QFrame {
        background-color: #3b4048;
        border: none;
    }
"""

RIGHT_PANEL_STYLE = """
    QFrame {
        background-color: #3b4048;
        border: none;
    }
"""

GRAPH_VIEW_STYLE = """
    QGraphicsView {
        background-color: #eaecee;
        border: none;
    }
"""