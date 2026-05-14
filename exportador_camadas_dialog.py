# exportador_camadas_dialog.py
# -*- coding: utf-8 -*-
"""
Diálogo para revisão e exportação de camadas
"""
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDialog, QTableWidgetItem, QPushButton, QFileDialog,
    QMessageBox, QHeaderView, QCheckBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'exportador_dialog.ui'))


class ExportadorDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(ExportadorDialog, self).__init__(parent)
        self.setupUi(self)
        self.camadas_para_exportar = []
        self.diretorio_saida = ""
        
        # Configurar tabela
        self.configurar_tabela()
        
        # Conectar botões
        self.btnSelecionarDiretorio.clicked.connect(self.selecionar_diretorio)
        self.btnAtualizarLista.clicked.connect(self.atualizar_lista_camadas)
        self.btnExportar.clicked.connect(self.exportar_camadas)
        self.btnCancelar.clicked.connect(self.reject)
        
        # Carregar camadas automaticamente
        self.atualizar_lista_camadas()

    def configurar_tabela(self):
        """Configura a tabela de camadas."""
        self.tabelaCamadas.setColumnCount(6)
        self.tabelaCamadas.setHorizontalHeaderLabels([
            "Exportar", "Camada Original", "Tipo", "Formato Saída", 
            "Nome Arquivo", "Caminho"
        ])
        
        # Redimensionar colunas
        header = self.tabelaCamadas.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

    def atualizar_lista_camadas(self):
        """Atualiza a lista de camadas na tabela."""
        self.tabelaCamadas.setRowCount(0)
        self.camadas_para_exportar = []
        
        layers = QgsProject.instance().mapLayers().values()
        
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                continue
                
            nome = layer.name()
            formato = None
            
            # Identificar formato pelo sufixo
            if nome.endswith('_geoportal'):
                formato = 'GeoJSON'
            elif nome.endswith('_inde'):
                formato = 'Shapefile'
            else:
                continue  # Pular camadas sem sufixo reconhecido
            
            # Adicionar à tabela
            row = self.tabelaCamadas.rowCount()
            self.tabelaCamadas.insertRow(row)
            
            # Checkbox para selecionar
            chk_exportar = QCheckBox()
            chk_exportar.setChecked(True)
            self.tabelaCamadas.setCellWidget(row, 0, chk_exportar)
            
            # Nome da camada (editável)
            self.tabelaCamadas.setItem(row, 1, QTableWidgetItem(nome))
            
            # Tipo de geometria
            geom_type = layer.geometryType()
            tipo_geo = {0: 'Ponto', 1: 'Linha', 2: 'Polígono'}.get(geom_type, 'Outro')
            self.tabelaCamadas.setItem(row, 2, QTableWidgetItem(tipo_geo))
            
            # Formato de saída (editável)
            item_formato = QTableWidgetItem(formato)
            self.tabelaCamadas.setItem(row, 3, item_formato)
            
            # Nome do arquivo (editável)
            nome_arquivo = nome.replace('_geoportal', '').replace('_inde', '')
            if formato == 'GeoJSON':
                nome_arquivo += '.geojson'
            else:
                nome_arquivo += '.shp'
            
            item_nome = QTableWidgetItem(nome_arquivo)
            self.tabelaCamadas.setItem(row, 4, item_nome)
            
            # Caminho completo
            if self.diretorio_saida:
                caminho = os.path.join(self.diretorio_saida, nome_arquivo)
                self.tabelaCamadas.setItem(row, 5, QTableWidgetItem(caminho))
            else:
                self.tabelaCamadas.setItem(row, 5, QTableWidgetItem("Selecione o diretório..."))
            
            self.camadas_para_exportar.append({
                'layer': layer,
                'nome_original': nome,
                'formato': formato
            })
        
        # Atualizar contador
        self.lblTotalCamadas.setText(f"Total de camadas: {self.tabelaCamadas.rowCount()}")

    def selecionar_diretorio(self):
        """Seleciona o diretório de saída."""
        directory = QFileDialog.getExistingDirectory(
            self, "Selecionar Diretório para Exportação"
        )
        
        if directory:
            self.diretorio_saida = directory
            self.txtDiretorio.setText(directory)
            
            # Atualizar caminhos na tabela
            for row in range(self.tabelaCamadas.rowCount()):
                nome_arquivo = self.tabelaCamadas.item(row, 4).text()
                caminho = os.path.join(directory, nome_arquivo)
                self.tabelaCamadas.setItem(row, 5, QTableWidgetItem(caminho))

    def exportar_camadas(self):
        """Exporta as camadas selecionadas."""
        if not self.diretorio_saida:
            QMessageBox.warning(
                self, "Aviso", 
                "Selecione um diretório de saída primeiro!"
            )
            return
        
        # Coletar camadas selecionadas
        selecionadas = []
        for row in range(self.tabelaCamadas.rowCount()):
            chk = self.tabelaCamadas.cellWidget(row, 0)
            if chk.isChecked():
                nome_arquivo = self.tabelaCamadas.item(row, 4).text()
                formato = self.tabelaCamadas.item(row, 3).text()
                
                selecionadas.append({
                    'layer': self.camadas_para_exportar[row]['layer'],
                    'nome_arquivo': nome_arquivo,
                    'formato': formato
                })
        
        if not selecionadas:
            QMessageBox.warning(
                self, "Aviso",
                "Nenhuma camada selecionada para exportação!"
            )
            return
        
        # Confirmar
        msg = f"Exportar {len(selecionadas)} camadas para:\n{self.diretorio_saida}?"
        reply = QMessageBox.question(
            self, "Confirmar Exportação", msg,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Exportar (aqui você pode usar as funções de exportação que já criamos)
        self.aceitar_exportacao(selecionadas)

    def aceitar_exportacao(self, selecionadas):
        """Aceita e retorna as configurações de exportação."""
        self.selecionadas = selecionadas
        self.accept()