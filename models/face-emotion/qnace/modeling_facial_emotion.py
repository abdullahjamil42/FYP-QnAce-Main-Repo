import torch
import torch.nn as nn
from transformers import PreTrainedModel, PretrainedConfig
from transformers.modeling_outputs import ImageClassifierOutput
import timm


class FacialEmotionConfig(PretrainedConfig):
    model_type = "facial_emotion_efficientnet"
    
    def __init__(
        self,
        num_classes=7,
        image_size=260,
        dropout=0.4,
        **kwargs
    ):
        self.num_classes = num_classes
        self.image_size = image_size
        self.dropout = dropout
        super().__init__(**kwargs)


class FacialEmotionModel(PreTrainedModel):
    config_class = FacialEmotionConfig
    
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_classes
        
        # EfficientNet-B2 backbone
        self.backbone = timm.create_model('efficientnet_b2.ra_in1k', pretrained=False)
        in_features = self.backbone.classifier.in_features
        
        # Custom classifier head
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=config.dropout),
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=config.dropout * 0.75),
            nn.Linear(512, config.num_classes)
        )
        
    def forward(self, pixel_values, labels=None):
        outputs = self.backbone(pixel_values)
        
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(outputs.view(-1, self.num_labels), labels.view(-1))
            
        return ImageClassifierOutput(
            loss=loss,
            logits=outputs,
            hidden_states=None,
            attentions=None,
        )