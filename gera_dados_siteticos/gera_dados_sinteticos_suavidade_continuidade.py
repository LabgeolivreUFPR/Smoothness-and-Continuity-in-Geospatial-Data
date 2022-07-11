"""
Model exported as python.
Name : tentativa_final
Group : 
With QGIS : 32403
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
import processing
from qgis.core import QgsProperty, edit,QgsProject,QgsProcessingUtils,QgsSpatialIndex,QgsProcessingParameterFeatureSink,QgsProcessingParameterRange
import random
import math
from itertools import product
import gc


class Modelo(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('areaestudo', 'area_estudo', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('tamanhodacelula', 'tamanho_da_celula', type=QgsProcessingParameterNumber.Integer, defaultValue=300))
        self.addParameter(QgsProcessingParameterFeatureSink('Final', 'final', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('suavidade', 'suavidade', type=QgsProcessingParameterNumber.Integer, minValue=0, maxValue=100, defaultValue=50))
        self.addParameter(QgsProcessingParameterNumber('continuidade', 'continuidade', type=QgsProcessingParameterNumber.Integer, minValue=0, maxValue=100, defaultValue=100))
        self.addParameter(QgsProcessingParameterNumber('val_max', 'valor maximo do fenomeno', type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=10000000, defaultValue=100))
        #self.addParameter(QgsProcessingParameterFeatureSink('Incrementado', 'incrementado', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Pontos_aleatorios', 'pontos_aleatorios', type=QgsProcessing.TypeVectorPoint, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        results = {}
        outputs = {}

        # Criar grade
        alg_params = {
            'CRS': 'ProjectCrs',
            'EXTENT': parameters['areaestudo'],
            'HOVERLAY': 0,
            'HSPACING': parameters['tamanhodacelula'],
            'TYPE': 4,  # Hexágono (Polígono)
            'VOVERLAY': 0,
            'VSPACING': parameters['tamanhodacelula'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CriarGrade'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
       
        
        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'valor',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Número inteiro
            'INPUT': outputs['CriarGrade']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AdicionarCampoTabelaDeAtributos'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
       
        layer_grade_inicial = QgsProcessingUtils.mapLayerFromString(outputs['AdicionarCampoTabelaDeAtributos']['OUTPUT'],context)
        ext = layer_grade_inicial.extent()
       

        ymin = ext.yMinimum()
        ymax = ext.yMaximum()
        numero_celulas_v = math.floor((ymax-ymin)/parameters['tamanhodacelula'])
        if parameters['suavidade']<60:
            MAXIMO_VALOR = int(parameters['suavidade']*1.6)
            #MAXIMO_VALOR =5
        else:
            MAXIMO_VALOR = 100
        n_altos = 100
        layer_grade_inicial = self.populate_val_grid('valor',layer_grade_inicial,MAXIMO_VALOR,1,numero_celulas_v,0)
            #results['Incrementado'] = outputs['AdicionarCampoDeAutoincremento']['OUTPUT']
        alg_params = {
            'INPUT':  parameters['areaestudo']
        }
        #processing.run("native:createspatialindex", alg_params, context=context)
        
          # Extrair por localização
        alg_params = {
            'INPUT': layer_grade_inicial.name(),
            'INTERSECT': parameters['areaestudo'],
            'PREDICATE': [6],  # contais
            'OUTPUT': parameters['Final']
        }
        outputs['ExtrairPorLocalizao'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        alg_params = {
            'FIELD_NAME': 'auto_id',
            'GROUP_FIELDS': [''],
            'INPUT': outputs['ExtrairPorLocalizao']['OUTPUT'],
            'MODULUS': 0,
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': '',
            'SORT_NULLS_FIRST': False,
            'START': 1,
            'OUTPUT':f'dados_sinteticos_suav_{parameters["suavidade"]}_contin_{parameters["continuidade"]}'
        }
        outputs['AdicionarCampoDeAutoincremento'] = processing.runAndLoadResults('native:addautoincrementalfield', alg_params, context=context, feedback=feedback)
    
        
        
        
        results['Final'] = outputs['AdicionarCampoDeAutoincremento']['OUTPUT']
        
        layer = QgsProcessingUtils.mapLayerFromString(outputs['AdicionarCampoDeAutoincremento']['OUTPUT'],context)
        
        #PARAMETRO_COLUNA_ID = layer.fields().indexOf('auto_id')
        #continuidade =parameters['continuidade']
        #suavidade = 1-parameters['suavidade']/100
        #dados_sinteticos = Dados_espaciais_sinteticos(layer,continuidade,suavidade,PARAMETRO_COLUNA_ID)
        #dados_sinteticos.configurar_continuidade(continuidade)
        #dados_sinteticos.adiciona_valores_sinteticos_layer()
        
        
        
        
        
        
        
        #PARAMETRO_COORDENADAS_ESQUERDA = layer.fields().indexOf('left')
        PARAMETRO_COLUNA_ID = layer.fields().indexOf('auto_id')
        PARAMETRO_COLUNA_VALOR = layer.fields().indexOf('valor')
        numero_poligonos = layer.featureCount()
        continuidade = parameters['continuidade']
        campo_valor = 'valor'
        
        #lista_vazios = Dados_sinteticos.configurar_continuidade(continuidade,numero_poligonos)
        
        #field_names = [field.name() for field in layer.fields()]
        
        p_s = Dados_sinteticos.set_layer(layer,PARAMETRO_COLUNA_ID,PARAMETRO_COLUNA_VALOR)
       
        
        
        d_s = Dados_sinteticos(layer=p_s[0], auto_id = p_s[1], objects = p_s[2], lista_de_ids_vazios = p_s[3], lista_de_ids_com_valor = p_s[4],dic_dif_viz_vazio=p_s[5])
        d_s.configurar_continuidade(continuidade)
        d_s.calcular_suavidade(campo_valor)
        if parameters['suavidade']>60:
            d_s.minimizar_suavidade3(campo_valor)
        suavidade = d_s.calcular_suavidade(campo_valor)
        
        results['suavidade_maxima'] = suavidade
        if parameters['suavidade'] > suavidade and parameters['suavidade']>60:
            results['resultado'] = 'Suavidade pretendida é maior que a suavidade minima que a grade suporta'
        
        else:
            suavidade = d_s.modifica_suavidade(parameters,suavidade,campo_valor)
            suavidade = d_s.calcular_suavidade(campo_valor)
        results['suavidade'] = suavidade
        d_s.adiciona_valores_sinteticos_layer(parameters)
        
        alg_params = {
            'INPUT': layer.name(),
            'MIN_DISTANCE': None,
            'STRATEGY': 0,  # Contagem de pontos
            'VALUE': QgsProperty.fromExpression('"valor"'),
            'OUTPUT': parameters['Pontos_aleatorios']
        }
        outputs['PontosAleatriosNoInteriorDosPolgonos'] = processing.run('qgis:randompointsinsidepolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Pontos_aleatorios'] = outputs['PontosAleatriosNoInteriorDosPolgonos']['OUTPUT']
        
        
        #alg_params = {
        #    'INPUT': results['Pontos_aleatorios']
        #}
        #processing.run("native:createspatialindex", alg_params, context=context)

        #Contagem de pontos em polígono
        #alg_params = {
        #    'CLASSFIELD': '',
        #    'FIELD': 'NUMPOINTS',
        #    'POINTS': outputs['PontosAleatriosNoInteriorDosPolgonos']['OUTPUT'],
        #    'POLYGONS': parameters['areaestudo'],
        #    'WEIGHT': '',
        #    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        #}
        #outputs['ContagemDePontosEmPolgono'] = processing.runAndLoadResults('native:countpointsinpolygon', alg_params, context=context, feedback=feedback)
        
        gc.collect()
        return results
        
        
    def populate_val_grid(self,idx,layer,init_val,second_val,n_celulas_v, n_altos):
        
        features=layer.getFeatures()
        field_idx = layer.fields().indexOf(idx)    
        field_idx2 = layer.fields().indexOf('auto_id')
        max_val =  init_val
        
        
        with edit(layer):
            for f in features:
                id = f.id()
                
                        
                if init_val == 100 or second_val == 100:
                    val = init_val if id % 2 == 0 else second_val
                else:
                    
                    val = random.SystemRandom().randint(1,100)
                if id == 5 or id == 25:
                    val = 100
                if id == 1 or id == 50:
                    val = 1
                
                layer.changeAttributeValue(id, field_idx, val)
                if id % n_celulas_v == 0:
                    aux = init_val
                    init_val = second_val
                    second_val = aux
                    #print('i',init_val,'sec',second_val)
                    
            """if init_val != 100 and second_val != 100:
                id_altos = []
                lista_ids=[x for x in range(1,layer.featureCount()+1)]
                for i in range(1,10):
                    r_id = random.SystemRandom().randint(1,len(lista_ids)-1)
                    id_alto = lista_ids.pop(r_id)
                    #print('idalto',id_alto)
                    layer.changeAttributeValue(id_alto, field_idx, 100)"""
                    
        
        return layer
        """
    def populate_val_grid(self,idx,layer,init_val,second_val,n_celulas_v,teste):
        features=layer.getFeatures()
        field_idx = layer.fields().indexOf(idx)    
        field_idx2 = layer.fields().indexOf('auto_id')
        with edit(layer):
            for f in features:
                id = f.id()
                
                val = init_val if id % 2 == 0 else second_val
                #print('val',val,'--','id',id)
                layer.changeAttributeValue(id, field_idx, val)
                if id % n_celulas_v == 0:
                    aux = init_val
                    init_val = second_val
                    second_val = aux
                    #print('i',init_val,'sec',second_val)
            
        return layer
        
    """    
        

    def name(self):
        return 'tentativa_final'

    def displayName(self):
        return 'tentativa_final'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Modelo()




class Poligono:
    """Classe que caracteriza uma celula de uma grade que divide o espaco geográfico.
        propriedades: 
            id: identificador da celula
            ids_poligonos_vizinhos: lista de identificadores dos poligonos vizinhos
            left: coordenada mais a esquerda da celula
            valor: valor do dado sintetico
            influencia: identifica se o valor da celula é menor ou maior que a media dos valores dos poligonos vizinhos
            porcentagem_maximo_valor_possivel: é a relacao entre a suavidade entre as celulas e os vizinhos e a 
                suavidade minima possivel
            is_modificado: indica se a celula foi modificada
        metodos:
            __str__: retorna uma string com as propriedades do objeto
        
    """

    def __init__(self,
        id,
        ids_poligonos_vizinhos,
        valor = None,
        influencia = None, 
        numero_de_vizinhos = None,
        porcentagem_maximo_valor_possivel = None,
        is_modificado = False,
        nviz_zero = 0,
        n_viz_viz = 0):

        self.id=id
        self.ids_poligonos_vizinhos=ids_poligonos_vizinhos
        self.valor = valor
        self.influencia = influencia
        self.numero_de_vizinhos = numero_de_vizinhos
        self.porcentagem_maximo_valor_possivel = porcentagem_maximo_valor_possivel
        self.is_modificado = is_modificado
        self.nviz_zero = nviz_zero
        self.n_viz_viz = n_viz_viz

    
    def __str__(self):
        return f'Poligono({self.id},{self.ids_poligonos_vizinhos},{self.valor})'
    
    def get_atr_viz(self):
            return self.numero_de_vizinhos
        
class Dados_sinteticos:
    """ Classe que caracteriza uma grade com dados que gerados sinteticamente
        propriedades:
            layer: camada do qgis que contem os poligonos com dados sinteticos
            auto_id: nome do campo que identifica o poligono
            objects: lista de objetos poligono
            lista_de_ids_vazios: lista de ids dos poligonos que nao possuem valor
            lista_de_ids_com_valor: lista de ids dos poligonos que possuem valor
        metodos:
            set_layer: metodo que cria um objeto Dados_espaciais_sinteticos a partir de um layer do qgis
    """

    def __init__(self,
                layer,
                auto_id,
                objects,
                lista_de_ids_vazios = [],
                lista_de_ids_com_valor = [],
                dic_dif_viz_vazio={},obj_ordered={},
                menor_valor = None,
                maior_valor = None):

        self.layer = layer
        self.objects = objects
        self.auto_id = auto_id
        self.lista_de_ids_vazios = lista_de_ids_vazios
        self.dic_dif_viz_vazio = dic_dif_viz_vazio
        self.lista_de_ids_com_valor = lista_de_ids_com_valor
        self.obj_ordered = obj_ordered
        self.menor_valor = menor_valor
        self.maior_valor = maior_valor
    
    @classmethod
    def set_layer(cls, layer,auto_id,field_valor):
        """ Metodo que cria um objeto Dados_sinteticos a partir de um layer do qgis
        campoetros:
                layer: layer do qgis
                auto_id: posicao do campo que identifica o poligono
                field_valor: posicao do campo que contem o valor do dado sintetico
            retorno:
                dados_sinteticos: 
                
                            """
        _NAME_FIELD_ID = auto_id
        _VALUE_IDX = field_valor

        lista_vazios = []
        dic_dif_viz_vazio ={}
        lista_com_valor = []
        polygon_objects = {}

        # cria um indice espacial para o layer
        features=layer.getFeatures()
        features_dict={}
        
        spatial_index = QgsSpatialIndex()
        for f in features:
            
            features_dict[f.id()]=f
            spatial_index.insertFeature(f)
        
        # cria um modelo topologico para o layer e encontra os poligonos com e sem valor
        for feat in features_dict:
            
            f=features_dict[feat]
            geom = f.geometry()            
            valor = f.attributes()[_VALUE_IDX]
            
            if valor != 0 and valor != None:
                lista_com_valor.append(feat)
            intersecting_ids = spatial_index.intersects(geom.boundingBox())
            neighbors = []
            vazios = []
            is_modi = False
            for intersecting_id in intersecting_ids:
                intersecting_f = features_dict[intersecting_id]               
                if (f != intersecting_f and not intersecting_f.geometry().disjoint(geom)):
                    val_v = intersecting_f[_VALUE_IDX]
                    if val_v == 0 or val_v == None:
                        vazios.append(intersecting_id)
                    neighbors.append(int(intersecting_f[_NAME_FIELD_ID]))
            
            #cria uma lista de objetos poligono para inserir no objeto Dados_sinteticos 
            
            pol = Poligono(feat,neighbors,valor,None,len(neighbors),None, is_modi,0,len(vazios))            
            polygon_objects[feat] = pol
            
       
        return layer,auto_id,polygon_objects,lista_vazios,lista_com_valor,dic_dif_viz_vazio
    
    def configurar_continuidade(self,continuidade):

        self.continuidade = continuidade
        numero_poligonos = len(self.objects)
        n_vazios = round(numero_poligonos*(100-self.continuidade)/100)
       
        lista_ids=[x for x in range(1,numero_poligonos+1)]
        lista_ids_vazios = []
        random.shuffle(lista_ids)

        for i in range(n_vazios):
                
                n = len(lista_ids)
                
                if n == 1:
                    random_id=0
                else:
                    random_id= random.SystemRandom().randint(0,n)
                random_id = random_id - 1
                #print(lista_ids)
                #print('random_id',random_id)
                indx = lista_ids[random_id]
                self.objects[indx].valor = 0
                
                ind = lista_ids.pop(random_id)
                
                lista_ids_vazios.append(ind)

        self.lista_de_ids_com_valor = lista_ids
        
        self.lista_de_ids_vazios = lista_ids_vazios        
        #self.configurar_suavidade(self.suavidade)
        
        return continuidade
        
        
        
    def calcular_suavidade(self,property):
        """ 
            Método que calcula a suavidade média da grade
        campoetros:  
                property: nome da propriedade que será calculada a suavidade
            funcao aninhada: 
                calcula_prop_aux
            retorno:
                suavidade: suavidade média da grade
        """
        
                   
        def calcula_prop_aux(vizinhos,val_j):
            """ Funcão que calcula para uma celula: 
                                    numero vizinho zeros
                                    maxima suavidade possivel
                                    suavidade da celula
                                    influencia
                input:  id - id da celula
                        ids_vizinhos - recebe os ids dos vizinhos
                        val - valor da celula
                output: suavidade da celula e contador (para ser somado na funcao principal)
            """
            n_zeros=0
            max_suavidade=0
            soma_suavi_celula=0            
            influencia=0
            cont=0
            n_viz_viz = 0
            soma_suavi_celula2 = 0 ## nao somo mais um valor quando é zero
            
            for v in vizinhos:
                cont += 1
                
                obj = self.objects[v]
                n_viz_viz += len(obj.ids_poligonos_vizinhos)
                val_v = obj.valor
                #val_v = obj.valor if type(obj.valor) == type(1) else 0
                #val_j = val_j if type(val_j) == type(1) else 0
                try:
                    dif_val= val_j-val_v
                except:
                    #print('val_j',val_j,'  ','val_v',val_v)
                    break;
                    
                
                soma_suavi_celula += abs(dif_val)
                soma_suavi_celula2 += abs(dif_val)
                influencia += dif_val
                if val_v == 0:
                    #conta duas vezes porque não este for não passa no vizinhos das celulas que tem valor 0
                    soma_suavi_celula += abs(dif_val)
                    cont += 1
                    
                    n_zeros+=1
                    
            
            try:
                suavidade_media = soma_suavi_celula/cont
                max_suavidade = soma_suavi_celula2/(n_zeros*100+(len(vizinhos)-n_zeros)*99)
                object.suavidade = suavidade_media
                object.suavidade = suavidade_media
                object.influencia = influencia
                object.numero_de_vizinhos_vazios = n_zeros
                object.porcentagem_maximo_valor_possivel = max_suavidade
                object.n_viz_viz = n_viz_viz
            except:
                #object.suavidade = object.suavidade
                #print(e)
                #print(cont,vizinhos)
                pass
                
            
            
            
            
            
            
            
            return soma_suavi_celula, cont,len(vizinhos)-n_zeros
                 
        
        suavidade = 0
        cont=0
        maior_v=0
        menor_v=100000000000
        dic_dif_viz_vazio = {}
        vazios = []
        dic_obj_ordered = {}
        ### percore a lista de indices de todos o poligono
        
        for j in self.objects:
            
            object=self.objects[j]
        
            viz = object.ids_poligonos_vizinhos

            ### pega o valor do fenomeno 
            val_j=object.valor
            maior_v = val_j if val_j > maior_v else maior_v 
            menor_v = val_j if val_j < menor_v else menor_v 
            
            if val_j == 0:
                #vazios.append(j)
                continue

            ### verifica se esse poligono é nao nulo ou não é vazio            
            
            soma_suav, cont1,dif_viz_vazio = calcula_prop_aux(viz,val_j)
            dic_obj_ordered[j]=object.n_viz_viz
            dic_dif_viz_vazio[j] = dif_viz_vazio
            suavidade += soma_suav
            cont += cont1
            
        self.menor_valor = menor_v
        self.maior_valor= maior_v
        dif_valor= maior_v-menor_v
        divisor= cont
        suavidade_media =suavidade/divisor
        #print('suavidade_media2',suavidade_media,'-','divisor','-','dif',dif_valor)
        suavidade_media = (suavidade_media/dif_valor)*100
        
        dic_obj_ordered=sorted(dic_obj_ordered.items(),key= lambda x:x[1],reverse=False)#reverse=False
        self.dic_dif_viz_vazio = dic_dif_viz_vazio
        #self.lista_de_ids_vazios = vazios
        self.obj_ordered = dic_obj_ordered
        
        
        return suavidade_media
    
   
    def minimizar_suavidade3(self,campo):
        
        ord = self.obj_ordered[0]
        id = ord[0]
        list_ob = self.objects
        #n_viz_viz = ord[1]
        def percorre_grid(id):
            obj = self.objects[id]
            min_mod = list_ob[n_viz_viz]
            list_ob.pop(id)
            obj_val = obj.valor
            viz = obj.ids_poligonos_vizinhos
            n_dif =0
            viz_nvizviz = True if obj.n_viz_viz == 9 else False
            menor_viz = 1000
            id_menor = None
            val_menor = None
            
            for v in viz:
                
                ob = self.objects[v]
                val_v = ob.valor
                is_mod = ob.is_modificado
                v_nvizviz = ob.n_viz_viz
                if v_nvizviz < menor_viz and is_mod == False:
                   menor_viz = v_nvizviz
                   id_menor = ob.id
                   val_menor = val_v
                if val_v == 0:
                    continue
                if viz_nvizviz:
                    if val_v == obj_val:
                        ob.valor = 1 if val_v == 100 else 1
                        ob.is_modificado = True
            if val_menor != 0:
                val_mod = 100 if val_menor==1 else 100
                self.objects[id_menor].valor = val_mod
                self.objects[id_menor].is_modificado = True
                
            if len(list_ob) >= len(self.objects) and id_menor is not None:
                percorre_grid(id_menor)
            elif len(list_ob) >= len(self.objects) and id_menor is None:
                id = list_ob[0].id
                percorre_grid(id)
                
        def encontrar_suavidade_alta(list_obj):
                
            for l_ob in reversed(list_obj):
                ob_l = self.objects[l_ob[0]]
                max_suavi = ob_l.porcentagem_maximo_valor_possivel
                valor = ob_l.valor
                if valor == 0:
                    continue
                if max_suavi != None and max_suavi < 0.5:    
                    #print('l_ob',l_ob,valor)
                    valor = 100 if valor == 1 else 1
                    self.calcular_suavidade(campo)
                ob_l.valor = valor
                
            for l_ob in reversed(list_obj):
                suave = self.calcular_suavidade(campo)
                ob_l = self.objects[l_ob[0]]
                val_para_mod = ob_l.valor
                max_suavi = ob_l.porcentagem_maximo_valor_possivel
                if val_para_mod == 0:
                    continue
                if max_suavi == 0.5:
                    ob_valor = 1 if val_para_mod == 100 else 1
                    ob_l.valor = ob_valor
                suave2 = self.calcular_suavidade(campo)
                if suave2 < suave:
                    ob_l.valor = val_para_mod
        #percorre_grid(1)                
        encontrar_suavidade_alta(self.obj_ordered)
    
    
   
    def modifica_suavidade(self,parameters,suavidade,campo_valor):
        
        indices = self.lista_de_ids_com_valor
        #print('indices',indices)
        len_ind=len(indices)-1
        
        suavidade_pretendida=parameters['suavidade']
        diferenca_suavidade=suavidade_pretendida-suavidade
        cont=0
        fator = 1
        fator_valor_aleatorio = int(suavidade_pretendida/100)
        fator_valor_aleatorio = fator_valor_aleatorio if fator_valor_aleatorio>1 else 1
        while abs(diferenca_suavidade)>0.9:
            try:
                obj = self.objects
                cont+=1
            
                id= random.SystemRandom().randint(0,len_ind)            
                random_id=indices[id]
            
            
                influencia =obj[random_id].influencia
            
                diferenca_suavidade=float(suavidade_pretendida-suavidade)
                valor=obj[random_id].valor
                menor = self.menor_valor
                maior = self.maior_valor
            
            
                if diferenca_suavidade>0:
                
                    if influencia>=0:
                   
                        #se a influencia do poligono é positiva e preciso aumentar a suavidade para igualar, entao soma para aumentar o valor do fenomeno
                        if valor == 100:
                            continue
                        else:
                            try:
                                random_v= random.SystemRandom().randint(1,fator_valor_aleatorio)
                                if int(valor+random_v*fator) <= 100:
                                    obj[random_id].valor=int(valor+random_v*fator)
                                else:
                                    obj[random_id].valor = 100
                            except:
                                pass
                                #print(valor)
                    
                    
                    elif influencia<0:
                        #se a influencia do poligono é negativa e preciso aumentar a suavidade para igualar, entao diminui para diminuir o valor do fenomeno
                        if valor <= 1:
                            continue
                        else:
                            try:
                                random_v= random.SystemRandom().randint(1,10)
                                if int(valor-random_v*fator) >=1:
                                    obj[random_id].valor=int(valor-random_v*fator)
                                else:
                                    obj[random_id].valor = 1                 
                            except:
                                pass
                                #print(valor)
                    
            
                elif diferenca_suavidade<0:

                    if influencia>=0:
                        if valor <= 1:
                            continue
                        else:
                        
                            try:
                                random_v= random.SystemRandom().randint(1,10)
                                if int(valor-random_v*fator) >=1:
                                    obj[random_id].valor=int(valor-random_v*fator)
                                else:
                                    obj[random_id].valor = 1
                            except:
                                pass
                                #print(valor)
                    
                   
                    
                    elif influencia<0:
                   
                        #se a influencia do poligono é negativa e preciso diminuir a suavidade para igualar, entao aumento o valor do fenomeno
                        if valor == 100:
                            continue
                        else:
                            try:
                                random_v= random.SystemRandom().randint(1,10)
                                if int(valor+random_v*fator) <= 100:
                                    obj[random_id].valor=int(valor+random_v*fator)
                                else:
                                    obj[random_id].valor = 100
                            except:
                                pass
                                #print(valor)
                            
                    
                   
                    
                suavidade =self.calcular_suavidade(campo_valor)
                #print(suavidade,'suavidade')
                diferenca_suavidade1=suavidade_pretendida-suavidade
                #fator= (diferenca_suavidade1-diferenca_suavidade)*2/diferenca_suavidade if diferenca_suavidade1>diferenca_suavidade else (diferenca_suavidade-diferenca_suavidade1)/diferenca_suavidade1
                diferenca_suavidade = diferenca_suavidade1
            except:
                #print(Error)
                pass
        return suavidade
        
        
    def adiciona_valores_sinteticos_layer(self,parameters):
        with edit(self.layer):
            field_idx = self.layer.fields().indexOf('valor')
            n_vizviz_idx = self.layer.fields().indexOf('n_vizviz')
            #field_id = self.layer.fields().indexOf('soma_das_ligacoes_dos_vizinhos')
            field_i = self.layer.fields().indexOf('n_v_zero')
           
            for i in range(1,len(self.objects)+1):
                v=self.objects[i].valor
                nvizviz = self.objects[i].n_viz_viz
                ##ver se é necessario add depois
                #s=self.objects[i].soma_das_ligacoes_dos_vizinhos
                
                #nvz=self.objects[i].n_v_zero
                if v==None:
                    v=0
                    
                if v != 0:
                    v = int(v*parameters['val_max']/100)
                self.layer.changeAttributeValue(i, field_idx, v)
                
                if n_vizviz_idx != -1:
                    self.layer.changeAttributeValue(i, n_vizviz_idx, nvizviz)
                
                #if type(nvz)==type(1):
                #    self.layer.changeAttributeValue(i+1, field_i, nvz)

