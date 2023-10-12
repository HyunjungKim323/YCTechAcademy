#-*- coding: utf-8 -*-
import torch, torchvision
import mmseg
import mmcv
import mmengine
import matplotlib.pyplot as plt
import os.path as osp
import os
import numpy as np
from PIL import Image
import cv2
from mmseg.registry import DATASETS
from mmseg.datasets import BaseSegDataset

from mmengine.runner import Runner
from mmseg.apis import init_model, inference_model, show_result_pyplot
from mmengine import Config
import argparse

def main():
    data_root = f'{args.data}'
    img_dir = 'train_img'
    ann_dir = 'train_label'
    img_dir2 = 'crop_image'
    ann_dir2 = 'crop_label'
    # define class and palette for better visualization
    classes = ('bg','building')
    palette = [[255,0,0],[0, 0, 255]]

    torch.manual_seed(0)

    @DATASETS.register_module()
    class SatelliteImageDataset(BaseSegDataset):
        METAINFO = dict(classes = classes, palette = palette,)
        def __init__(self, **kwargs):
            super().__init__(img_suffix='.png', seg_map_suffix='.png', **kwargs)


    config_path = os.path.join(args.mmseg,'configs/segformer/segformer_mit-b5_8xb1-160k_cityscapes-1024x1024.py')
    cfg = Config.fromfile(config_path)
    #print(f'Config:\n{cfg.pretty_text}')


    cfg.norm_cfg = dict(type='BN', requires_grad=True)
    cfg.crop_size = (224, 224)
    cfg.model.data_preprocessor.size = cfg.crop_size
    #cfg.model.backbone.norm_cfg = cfg.norm_cfg
    cfg.model.decode_head.norm_cfg = cfg.norm_cfg
    #cfg.model.auxiliary_head.norm_cfg = cfg.norm_cfg
    # modify num classes of the model in decode/auxiliary head
    cfg.model.decode_head.num_classes = 2
    #cfg.model.auxiliary_head.num_classes = 2

    # Modify dataset type and path
    cfg.dataset_type = 'SatelliteImageDataset'
    cfg.data_root = data_root


    class_weight = [0.5, 1.0] 


    loss_list = []
    #loss_list.append(dict(type='CrossEntropyLoss',  use_sigmoid=False, loss_weight = 1.0, class_weight=class_weight)) 
    loss_list.append(dict(type='FocalLoss',use_sigmoid=True,loss_name='loss_focal', loss_weight = 1.0))           
    cfg.model.decode_head.loss_decode = loss_list



    cfg.train_dataloader.batch_size = 16

    cfg.img_norm_cfg = dict(
        mean=[0.32519105, 0.35761357, 0.34220385], std=[0.16558432, 0.17289196, 0.19330389], to_rgb=True
        #mean=[123.675, 116.28, 103.53], std=[58.395, 57.12, 57.375], to_rgb=True
    )

    cfg.train_pipeline = [
        dict(type='LoadImageFromFile'),
        dict(type='LoadAnnotations'),
        #dict(type='RandomCrop', crop_size=cfg.crop_size),
        dict(type='RandomFlip', prob=0.5),
        #dict(type='PhotoMetricDistortion'),
        #dict(type='Normalize', **cfg.img_norm_cfg),
        dict(type='PackSegInputs')
    ]

    cfg.test_pipeline = [
        dict(type='LoadImageFromFile'),
        #dict(type='Normalize', **cfg.img_norm_cfg),
        dict(type='LoadAnnotations'),
        dict(type='PackSegInputs')
    ]


    cfg.train_dataloader.dataset.type = cfg.dataset_type
    cfg.train_dataloader.dataset.data_root = cfg.data_root
    cfg.train_dataloader.dataset.data_prefix = dict(img_path=img_dir2, seg_map_path=ann_dir2)
    cfg.train_dataloader.dataset.pipeline = cfg.train_pipeline
    cfg.train_dataloader.dataset.ann_file = os.path.join(args.data, 'splits/crop_train.txt')

    cfg.val_dataloader.dataset.type = cfg.dataset_type
    cfg.val_dataloader.dataset.data_root = cfg.data_root
    cfg.val_dataloader.dataset.data_prefix = dict(img_path=img_dir2, seg_map_path=ann_dir2)
    cfg.val_dataloader.dataset.pipeline = cfg.test_pipeline
    cfg.val_dataloader.dataset.ann_file = os.path.join(args.data, 'splits/crop_val.txt')

    cfg.test_dataloader = cfg.val_dataloader

    # Load the pretrained weights
    cfg.load_from = './checkpoints/segformer_mit-b5_8xb1_1024x1024_160k_cityscapes_20211206_072934-87a052ec.pth'


    # Set up working dir to save files and logs.
    cfg.work_dir = './segformer_modelA'

    cfg.train_cfg.max_iters = 53550
    cfg.train_cfg.val_interval = 8925
    cfg.default_hooks.logger.interval = 1000
    cfg.default_hooks.checkpoint.interval = 8925

    # We can also use tensorboard to log the training process
    cfg.vis_backends = [dict(type='LocalVisBackend'), dict(type='TensorboardVisBackend')] 
    cfg.visualizer = dict(type='SegLocalVisualizer',vis_backends=cfg.vis_backends,name='visualizer') 


    # Set seed to facilitate reproducing the result
    cfg['randomness'] = dict(seed=0)


    # Let's have a look at the final config used for training
    print(f'Config:\n{cfg.pretty_text}')

    runner = Runner.from_cfg(cfg)

    print("runner.train")
    # start training
    runner.train()

    print("training end")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mmseg', 
                        type=str, 
                        required=True,
                        help='path to mmsegmentation folder')

    parser.add_argument('--data', 
                        type=str, 
                        required=True,
                        help='path to dataset with train_img, train_label, crop_img, crop_label and splits within it')
    
    args = parser.parse_args()
    main()