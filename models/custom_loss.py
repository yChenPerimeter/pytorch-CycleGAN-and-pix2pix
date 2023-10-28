# -*- coding: utf-8 -*-
"""
Created on Mon Jul 10 09:33:26 2023
Modified, 2023 1024

@author: MarkNguyen,
Modfier: Youwei Credit to Author : alper111 , https://gist.github.com/alper111/8233cdb0414b4cb5853f2f730ab95a49
"""

import torch
from torch import nn
import torchvision
from pytorch_msssim import ssim,ms_ssim
from torchvision.models.vgg import  VGG19_Weights, VGG19_Weights

def custom_loss(output, target):
    ssim_loss = 1 - ssim(output, target, data_range=1.0, size_average=True)
    L1 = nn.L1Loss()
    return 0.5*L1(output, target) + 0.5*ssim_loss

class VGGPerceptualLoss(torch.nn.Module):
    def __init__(self, resize=True):
        super(VGGPerceptualLoss, self).__init__()
        blocks = []
        blocks.append(torchvision.models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[:4].eval())
        blocks.append(torchvision.models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[4:9].eval())
        blocks.append(torchvision.models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[9:18].eval())
        blocks.append(torchvision.models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[18:27].eval())
        #blocks.append(torchvision.models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[27:36].eval())
        for bl in blocks:
            for p in bl.parameters():
                p.requires_grad = False
        self.blocks = torch.nn.ModuleList(blocks)
        self.transform = torch.nn.functional.interpolate
        self.resize = resize
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, input, target, feature_layers=[0, 1, 2, 3, 4], style_layers=[]):
        if input.shape[1] != 3:
            input = input.repeat(1, 3, 1, 1)
            target = target.repeat(1, 3, 1, 1)
        input = (input-self.mean) / self.std
        target = (target-self.mean) / self.std
        if self.resize:
            input = self.transform(input, mode='bilinear', size=(420, 420), align_corners=False)
            target = self.transform(target, mode='bilinear', size=(420, 420), align_corners=False)
        loss = 0.0
        x = input
        y = target
        for i, block in enumerate(self.blocks):
            x = block(x)
            y = block(y)
            if i in feature_layers:
                #loss += torch.nn.functional.l1_loss(x, y)
                loss += custom_loss(x, y)
            if i in style_layers:
                act_x = x.reshape(x.shape[0], x.shape[1], -1)
                act_y = y.reshape(y.shape[0], y.shape[1], -1)
                gram_x = act_x @ act_x.permute(0, 2, 1)
                gram_y = act_y @ act_y.permute(0, 2, 1)
                #loss += torch.nn.functional.l1_loss(gram_x, gram_y)
                loss += custom_loss(gram_x, gram_y)
        return loss