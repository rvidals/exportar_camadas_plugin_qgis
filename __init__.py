# -*- coding: utf-8 -*-
"""
Exportador de Camadas - Plugin para QGIS
"""
from .exportador_camadas import ExportadorCamadasPlugin

def classFactory(iface):
    return ExportadorCamadasPlugin(iface)