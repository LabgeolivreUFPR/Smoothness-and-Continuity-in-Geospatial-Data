"""
Model exported as python.
Name : Calculo da suavidade
Group : 
With QGIS : 32203
"""

from qgis.core import QgsProcessing,QgsProcessingUtils,QgsSpatialIndex
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
import processing


class CalculoSuavidade(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('poligono', 'poligono', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('campodecontagem', 'campo_de_contagem', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='poligono', allowMultiple=False, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(1, model_feedback)
        results = {}
        outputs = {}
        
        alg_params = {
            'COLUMN': ['auto_id'],
            'INPUT': parameters['poligono'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DescartarCampos'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        # Adicionar campo de autoincremento
        alg_params = {
            'FIELD_NAME': 'auto_id',
            'GROUP_FIELDS': [''],
            'INPUT': outputs['DescartarCampos']['OUTPUT'],
            'MODULUS': 0,
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': '',
            'SORT_NULLS_FIRST': False,
            'START': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['AdicionarCampoDeAutoincremento'] = processing.run('native:addautoincrementalfield', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        layer = QgsProcessingUtils.mapLayerFromString(outputs['AdicionarCampoDeAutoincremento']['OUTPUT'],context)
        resultado,indices = self.return_vizinhos(layer,parameters)
        suavidade,numero_ligacoes,modelo_topologico,continuidade=self.calculo_influencia(len(indices),resultado)
        results['layer']=parameters['poligono']
        results['suavidade']=suavidade
        results['continuidade']=continuidade
        
        
        return results

    def name(self):
        return 'Calculo da Suavidade'

    def displayName(self):
        return 'Calculo da Suavidade'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return CalculoSuavidade()
    
      
    def return_vizinhos(self,layer,parameters):
        # faz um dicionario {id: feicao) do layer passado
        field_idx = layer.fields().indexOf(parameters['campodecontagem'])
        
        
        feature_dict = {f.id(): f for f in layer.getFeatures()}
        _NAME_FIELD = 'auto_id'
        # Build a spatial index
        index = QgsSpatialIndex()
        
        #insere as feições no indice espacial
        for f in feature_dict.values():
            index.insertFeature(f)
        
        indices=[] ### container de todos os ids
        n=[]
        
        # Loop through all features and find features that touch each feature
        for f in feature_dict.values():
            ### acha os provaveis poligonos que intersectam com o poligono
           
           
            valor=f.attributes()[field_idx]
            indices.append(f.attributes()[-1])
            geom = f.geometry()
            intersecting_ids = index.intersects(geom.boundingBox())
            neighbors = []
            
            
           
            ### filtra quais poligonos de fato intersectam com o poligono
            for intersecting_id in intersecting_ids:
                
                intersecting_f = feature_dict[intersecting_id]
               
                if (f != intersecting_f and not intersecting_f.geometry().disjoint(geom)):
                    
                    neighbors.append(intersecting_f[_NAME_FIELD])
            n.append({'ligacoes':neighbors,'val':valor,'influencia':''})
            
        ### gera um dicionario {id:{ligacoes:[3..4...], val:'',influencia:''}}
        resultado=dict(zip(indices,n))
        
        
        return resultado,indices
        
    def calculo_influencia(self,n_indices,resultado):
        ## inicializa a variaveis para armazenar a suavidade media,o numero de vizinhacas total, o maior valor e o menor valor
        influencia_media = 0
        cont=0
        maior_v=0
        menor_v=10000000000
        n_zeros = 0
        ### percore a lista de indices de todos o poligono
        for j in range(n_indices):
            
            ### pega o valor do fenomeno 
            val_j=resultado[j]['val']
            if val_j == 0 or val_j == None:
                n_zeros += 1 
            ### verifica se esse poligono é nao nulo ou não é vazio
            if val_j != None and val_j != 0:
                ### testa se o valor é o maior
                if val_j>maior_v:
                    maior_v=val_j
                ### pega os ids dos vizinhos do poligono
                l=resultado[j]['ligacoes']
                
                ### armazena a diferenca do valor do poligono para o seus vizinhos
                influencia=0
                
                ### percorre todos o vizinhos
                for k in l:
                    ### pega o valor do vizinho
                    val_k=resultado[k]['val']
                    
                    ## soma essa vizinhanca
                    cont+=1
                    
                    ### verifica se o vizinho não é vazio
                    if val_k != None and val_k != 0:
                        ### calcula a diferenca entre o valor do poligono e o vizinho, soma a variavel 
                        influencia+=abs(val_j-val_k)
                        
                        ### tenta achar o menor valor de fenomeno gerado
                        if val_k < menor_v:
                            menor_v=val_k
                        
                    ### se o vizinho é vazio coloca o valor 0 nele 
                    elif val_k == None or val_k == 0:
                        
                        #e soma o valor deste poligono na influencia
                        resultado[k]['val']= 0
                        if val_k < menor_v:
                            menor_v=val_k
                        #e soma o valor deste poligono na influencia                       
                        influencia+=val_j*2
                        cont+=1
                ### soma a influencia absoluta para depois calcular a suavidade media
                influencia_media+=abs(influencia)
                

                ### salva a influencia do poligono (se é negativa em média o valor do fenomeno é menor que seus vizinhos e o oposto se for positivo)
                resultado[j]['influencia']=influencia
        ### acha a diferenca entre o valor maximo e o minimo do fenomeno
        dif_valor=maior_v-menor_v
        #print('difvalor',dif_valor)
        ### aqui acha o fator de normalizacao numero de vizinhancas* (maior valor -menor valor)
        divisor=cont*dif_valor
        #print('cont',cont)
        #print('influencia',100*influencia_media/divisor)
        print(n_zeros,'nzero')
        print(n_indices,'nindices')
        ## retorna o modelo topologico com a influencia de cada poligono, a suavidade media, fator de normalizacao
        return 100*influencia_media/divisor,cont,resultado,100*(n_indices-n_zeros)/n_indices
    
   