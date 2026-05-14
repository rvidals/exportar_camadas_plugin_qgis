# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProject, 
    QgsVectorFileWriter, 
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsLayerTreeGroup,  # ← ADICIONADO
    QgsApplication      # ← ADICIONADO
)

from .exportador_camadas_dialog import ExportadorDialog


class ExportadorCamadasPlugin:
    """Plugin para exportar camadas automaticamente."""
    
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = 'Exportador de Camadas'

    def initGui(self):
        """Inicializa a interface gráfica do plugin."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        
        # Ação principal: Revisar antes de exportar
        self.action_revisar = QAction(
            QIcon(icon_path),
            'Revisar e Exportar Camadas',
            self.iface.mainWindow()
        )
        self.action_revisar.triggered.connect(self.abrir_dialogo_revisao)
        self.iface.addPluginToMenu(self.menu, self.action_revisar)
        self.iface.addToolBarIcon(self.action_revisar)
        self.actions.append(self.action_revisar)
        
        # Exportar todas as camadas (automático)
        self.action_exportar_todas = QAction(
            QIcon(icon_path),
            'Exportar Todas (Automático)',
            self.iface.mainWindow()
        )
        self.action_exportar_todas.triggered.connect(self.exportar_todas_camadas)
        self.iface.addPluginToMenu(self.menu, self.action_exportar_todas)
        self.actions.append(self.action_exportar_todas)
        
        # Exportar camadas selecionadas (automático)
        self.action_exportar_selecionadas = QAction(
            QIcon(icon_path),
            'Exportar Selecionadas (Automático)',
            self.iface.mainWindow()
        )
        self.action_exportar_selecionadas.triggered.connect(self.exportar_camadas_selecionadas)
        self.iface.addPluginToMenu(self.menu, self.action_exportar_selecionadas)
        self.actions.append(self.action_exportar_selecionadas)

    def unload(self):
        """Remove o plugin e seus componentes."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    # ========== NOVOS MÉTODOS ==========
    
    def abrir_dialogo_revisao(self):
        """Abre o diálogo para revisar camadas antes de exportar."""
        dialog = ExportadorDialog(self.iface.mainWindow())
        
        if dialog.exec_():
            selecionadas = dialog.selecionadas
            diretorio = dialog.diretorio_saida
            
            if selecionadas:
                self.executar_exportacao(selecionadas, diretorio)

    def executar_exportacao(self, selecionadas, diretorio):
        """Executa a exportação das camadas selecionadas no diálogo."""
        sucessos = []
        erros = []
        camadas_exportadas = []  # Lista para guardar os caminhos dos arquivos
        
        # Barra de progresso
        QgsApplication.processEvents()
        
        for item in selecionadas:
            layer = item['layer']
            nome_arquivo = item['nome_arquivo']
            formato = item['formato']
            
            try:
                if formato == 'GeoJSON':
                    caminho = self.exportar_geojson_personalizado(layer, diretorio, nome_arquivo)
                    sucessos.append(f"✅ {layer.name()} → {nome_arquivo}")
                    camadas_exportadas.append({
                        'caminho': caminho,
                        'nome': nome_arquivo,
                        'formato': 'GeoJSON',
                        'layer_original': layer.name()
                    })
                elif formato == 'Shapefile':
                    caminho = self.exportar_shapefile_personalizado(layer, diretorio, nome_arquivo)
                    sucessos.append(f"✅ {layer.name()} → {nome_arquivo}")
                    camadas_exportadas.append({
                        'caminho': caminho,
                        'nome': nome_arquivo,
                        'formato': 'Shapefile',
                        'layer_original': layer.name()
                    })
            except Exception as e:
                erros.append(f"❌ {layer.name()}: {str(e)}")
        
        # Adicionar camadas exportadas ao QGIS
        if camadas_exportadas:
            self.adicionar_camadas_ao_projeto(camadas_exportadas)
        
        # Mostrar resultado
        resultado = "RESULTADO DA EXPORTAÇÃO\n\n"
        if sucessos:
            resultado += "✅ Sucessos:\n"
            for s in sucessos:
                resultado += f"  • {s}\n"
        if erros:
            if sucessos:
                resultado += "\n"
            resultado += "❌ Erros:\n"
            for e in erros:
                resultado += f"  • {e}\n"
        
        if camadas_exportadas:
            resultado += f"\n📂 {len(camadas_exportadas)} camada(s) adicionada(s) ao projeto no grupo 'Exportação'"
        
        QMessageBox.information(
            self.iface.mainWindow(),
            "Exportação Concluída",
            resultado
        )

    def adicionar_camadas_ao_projeto(self, camadas_exportadas):
        """
        Adiciona as camadas exportadas ao projeto QGIS dentro de um grupo.
        
        Args:
            camadas_exportadas (list): Lista de dicionários com informações das camadas
        """
        root = QgsProject.instance().layerTreeRoot()
        
        # Criar ou obter o grupo "Exportação"
        grupo_nome = "Exportação"
        grupo = root.findGroup(grupo_nome)
        
        if not grupo:
            grupo = root.addGroup(grupo_nome)
        
        # Adicionar cada camada ao grupo
        for camada_info in camadas_exportadas:
            caminho = camada_info['caminho']
            nome = camada_info['nome']
            formato = camada_info['formato']
            
            # Criar nome amigável para a camada
            nome_camada = nome.replace('.geojson', '').replace('.shp', '')
            nome_camada = f"{nome_camada} ({formato})"
            
            # Carregar a camada
            if formato == 'GeoJSON':
                layer = QgsVectorLayer(caminho, nome_camada, 'ogr')
            elif formato == 'Shapefile':
                layer = QgsVectorLayer(caminho, nome_camada, 'ogr')
            
            # Verificar se a camada é válida
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer, False)  # False = não adiciona ao root
                grupo.addLayer(layer)  # Adiciona ao grupo
            else:
                print(f"Erro ao carregar camada: {nome_camada}")

    def exportar_geojson_personalizado(self, layer, diretorio, nome_arquivo):
        """
        Exporta uma camada para GeoJSON com nome personalizado.
        
        Returns:
            str: Caminho completo do arquivo exportado
        """
        caminho_completo = os.path.join(diretorio, nome_arquivo)
        
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GeoJSON"
        options.fileEncoding = "UTF-8"
        
        # Transformar CRS para WGS84 (padrão para GeoJSON)
        if layer.crs().authid() != 'EPSG:4326':
            options.ct = QgsCoordinateTransform(
                layer.crs(),
                QgsCoordinateReferenceSystem('EPSG:4326'),
                QgsProject.instance()
            )
        
        error = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, 
            caminho_completo,
            QgsProject.instance().transformContext(),
            options
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            raise Exception(f"Erro ao exportar GeoJSON: {error[1]}")
        
        return caminho_completo

    def exportar_shapefile_personalizado(self, layer, diretorio, nome_arquivo):
        """
        Exporta uma camada para Shapefile com nome personalizado.
        
        Returns:
            str: Caminho completo do arquivo exportado
        """
        # Criar subdiretório para o shapefile
        nome_base = nome_arquivo.replace('.shp', '')
        diretorio_shp = os.path.join(diretorio, nome_base)
        os.makedirs(diretorio_shp, exist_ok=True)
        
        caminho_completo = os.path.join(diretorio_shp, nome_arquivo)
        
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        
        error = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, 
            caminho_completo,
            QgsProject.instance().transformContext(),
            options
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            raise Exception(f"Erro ao exportar Shapefile: {error[1]}")
        
        return caminho_completo

    # ========== MÉTODOS ORIGINAIS (ATUALIZADOS) ==========
    
    def obter_camadas_para_exportar(self, apenas_selecionadas=False):
        """Obtém as camadas que precisam ser exportadas baseado no sufixo."""
        camadas = {
            'geojson': [],
            'shp': []
        }
        
        if apenas_selecionadas:
            layers = self.iface.layerTreeView().selectedLayers()
        else:
            layers = QgsProject.instance().mapLayers().values()
        
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                continue
                
            nome_camada = layer.name()
            
            if nome_camada.endswith('_geoportal'):
                camadas['geojson'].append(layer)
            elif nome_camada.endswith('_inde'):
                camadas['shp'].append(layer)
                
        return camadas

    def escolher_diretorio(self):
        """Abre diálogo para escolher o diretório de exportação."""
        settings = QSettings()
        last_dir = settings.value("ExportadorCamadas/ultimo_diretorio", "")
        
        directory = QFileDialog.getExistingDirectory(
            self.iface.mainWindow(),
            "Selecionar Diretório para Exportação",
            last_dir
        )
        
        if directory:
            settings.setValue("ExportadorCamadas/ultimo_diretorio", directory)
            
        return directory

    def exportar_geojson(self, layer, diretorio):
        """Exporta uma camada para GeoJSON (método original)."""
        try:
            nome_arquivo = layer.name().replace('_geoportal', '') + '.geojson'
            caminho_completo = os.path.join(diretorio, nome_arquivo)
            
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GeoJSON"
            options.fileEncoding = "UTF-8"
            
            if layer.crs().authid() != 'EPSG:4326':
                options.ct = QgsCoordinateTransform(
                    layer.crs(),
                    QgsCoordinateReferenceSystem('EPSG:4326'),
                    QgsProject.instance()
                )
            
            error = QgsVectorFileWriter.writeAsVectorFormatV2(
                layer,
                caminho_completo,
                QgsProject.instance().transformContext(),
                options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                return True, f"GeoJSON exportado com sucesso: {nome_arquivo}", caminho_completo
            else:
                return False, f"Erro ao exportar GeoJSON: {error}", None
                
        except Exception as e:
            return False, f"Erro ao exportar GeoJSON: {str(e)}", None

    def exportar_shapefile(self, layer, diretorio):
        """Exporta uma camada para Shapefile (método original)."""
        try:
            nome_camada = layer.name().replace('_inde', '')
            diretorio_shp = os.path.join(diretorio, nome_camada)
            os.makedirs(diretorio_shp, exist_ok=True)
            
            nome_arquivo = nome_camada + '.shp'
            caminho_completo = os.path.join(diretorio_shp, nome_arquivo)
            
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "UTF-8"
            
            error = QgsVectorFileWriter.writeAsVectorFormatV2(
                layer,
                caminho_completo,
                QgsProject.instance().transformContext(),
                options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                return True, f"Shapefile exportado com sucesso: {nome_camada}", caminho_completo
            else:
                return False, f"Erro ao exportar Shapefile: {error}", None
                
        except Exception as e:
            return False, f"Erro ao exportar Shapefile: {str(e)}", None

    def exportar_camadas(self, apenas_selecionadas=False):
        """Método principal para exportar camadas (ATUALIZADO)."""
        diretorio = self.escolher_diretorio()
        if not diretorio:
            return
        
        camadas = self.obter_camadas_para_exportar(apenas_selecionadas)
        
        total_geojson = len(camadas['geojson'])
        total_shp = len(camadas['shp'])
        
        if total_geojson == 0 and total_shp == 0:
            QMessageBox.information(
                self.iface.mainWindow(),
                "Exportador de Camadas",
                "Nenhuma camada encontrada com os sufixos _geoportal ou _inde!"
            )
            return
        
        mensagem = f"Camadas encontradas:\n"
        mensagem += f"• {total_geojson} camadas para GeoJSON (_geoportal)\n"
        mensagem += f"• {total_shp} camadas para Shapefile (_inde)\n\n"
        mensagem += f"Exportar para: {diretorio}\n\n"
        mensagem += "Deseja continuar?"
        
        resposta = QMessageBox.question(
            self.iface.mainWindow(),
            "Confirmar Exportação",
            mensagem,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if resposta != QMessageBox.Yes:
            return
        
        sucessos = []
        erros = []
        camadas_exportadas = []
        
        # Exportar GeoJSONs
        for layer in camadas['geojson']:
            sucesso, msg, caminho = self.exportar_geojson(layer, diretorio)
            if sucesso:
                sucessos.append(msg)
                camadas_exportadas.append({
                    'caminho': caminho,
                    'nome': os.path.basename(caminho),
                    'formato': 'GeoJSON',
                    'layer_original': layer.name()
                })
            else:
                erros.append(msg)
        
        # Exportar Shapefiles
        for layer in camadas['shp']:
            sucesso, msg, caminho = self.exportar_shapefile(layer, diretorio)
            if sucesso:
                sucessos.append(msg)
                camadas_exportadas.append({
                    'caminho': caminho,
                    'nome': os.path.basename(caminho),
                    'formato': 'Shapefile',
                    'layer_original': layer.name()
                })
            else:
                erros.append(msg)
        
        # Adicionar camadas exportadas ao projeto
        if camadas_exportadas:
            self.adicionar_camadas_ao_projeto(camadas_exportadas)
        
        # Mostrar resultado
        resultado = "RESULTADO DA EXPORTAÇÃO\n\n"
        
        if sucessos:
            resultado += "✅ Sucessos:\n"
            for s in sucessos:
                resultado += f"  • {s}\n"
        
        if erros:
            if sucessos:
                resultado += "\n"
            resultado += "❌ Erros:\n"
            for e in erros:
                resultado += f"  • {e}\n"
        
        if camadas_exportadas:
            resultado += f"\n📂 {len(camadas_exportadas)} camada(s) adicionada(s) ao projeto no grupo 'Exportação'"
        
        QMessageBox.information(
            self.iface.mainWindow(),
            "Exportação Concluída",
            resultado
        )

    def exportar_todas_camadas(self):
        """Exporta todas as camadas do projeto."""
        self.exportar_camadas(apenas_selecionadas=False)

    def exportar_camadas_selecionadas(self):
        """Exporta apenas as camadas selecionadas no painel de camadas."""
        self.exportar_camadas(apenas_selecionadas=True)