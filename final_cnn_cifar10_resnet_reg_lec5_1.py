# -*- coding: utf-8 -*-
"""Final_Cnn_Cifar10_resnet_reg_lec5_1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1hQDK3yoW0D9bTd3Ep1q8dA7L0hKkp3vS
"""

# Commented out IPython magic to ensure Python compatibility.
import os
import torch 
import torchvision

import torch.nn as nn 
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from torchvision.datasets import ImageFolder
from torchvision.datasets.utils import download_url
from torch.utils.data import DataLoader
import torchvision.transforms as tt 
from torch.utils.data import random_split
from torchvision.utils import make_grid
import matplotlib.pyplot as plt
# %matplotlib inline

plt.rcParams['figure.facecolor'] = '#ffffff'

from torch.utils.tensorboard import SummaryWriter

from torchvision.datasets.utils import download_and_extract_archive

    ## download mini-imagenet
url = "https://s3.amazonaws.com/fast-ai-imageclas/cifar10.tgz"
filename ='Imagenet.tgz'
root = '~/tmp/'
download_and_extract_archive(url, root, filename)

data_dir = '/content/Imagenet.tgz/cifar10'
print(os.listdir(data_dir))
classes = os.listdir('/content/Imagenet.tgz/cifar10/train')
print(classes)
classes[2]

train_tfms = tt.Compose([tt.ToTensor()])
valid_tfms = tt.Compose([tt.ToTensor()])

# PyTorch datasets
train_ds = ImageFolder(data_dir + '/train',train_tfms)
valid_ds = ImageFolder(data_dir + '/test',valid_tfms)
len(valid_ds)

batch_size=104
train_loader = DataLoader(train_ds, batch_size, shuffle=True, num_workers=4, pin_memory=True)
val_loader = DataLoader(valid_ds, batch_size*2, num_workers=4, pin_memory=True)

image, label = train_ds[100]
print(image.shape)
plt.imshow(image.permute(1, 2, 0))

print('Label:',train_ds.classes[label])

for images, _ in train_loader:
    print('images.shape:', images.shape)
    plt.figure(figsize=(16,8))
    plt.axis('off')
    plt.imshow(make_grid(images, nrow=16).permute((1, 2, 0)))
    break

loader=DataLoader(train_ds, batch_size=len(train_ds), shuffle=True, num_workers=4, pin_memory=True)
data=next(iter(train_loader))

mean=data[0].mean()
std=data[0].std()
mean, std

plt.hist(data[0].flatten())
plt.axvline(data[0].mean())

train_normalised = tt.Compose([tt.ToTensor(),tt.Normalize(mean,std)])
train_nz = ImageFolder(data_dir + '/train',train_normalised)

loader_normalised=DataLoader(train_nz, batch_size=len(train_nz),num_workers=2)
data1=next(iter(loader_normalised))

mean_normalised=data1[0].mean()
std_normalised=data1[0].std()
mean_normalised,std_normalised

plt.hist(data1[0].flatten())
plt.axvline(data1[0].mean())

train_tfms = tt.Compose([tt.RandomCrop(32, padding=4, padding_mode='reflect'), 
                         tt.RandomHorizontalFlip(), 
                         
                         tt.ToTensor(), 
                         tt.Normalize(mean,std)])
train_ds = ImageFolder(data_dir+'/train', train_tfms)

valid_tfms = tt.Compose([tt.ToTensor(), tt.Normalize(mean,std)])

train_ds = ImageFolder(data_dir+'/train', train_tfms)
valid_ds = ImageFolder(data_dir+'/test', valid_tfms)

train_dl = DataLoader(train_ds, batch_size, shuffle=True, num_workers=2, pin_memory=True)
valid_dl = DataLoader(valid_ds, batch_size*2, num_workers=2, pin_memory=True)

batch_size=104
train_loader = DataLoader(train_ds, batch_size, shuffle=True, num_workers=2, pin_memory=True)
val_loader = DataLoader(valid_ds, batch_size*2, num_workers=2, pin_memory=True)

def get_num_correct(preds, labels):
    return preds.argmax(dim=1).eq(labels).sum().item()

for images, _ in train_loader:
    print('images.shape:', images.shape)
    plt.figure(figsize=(16,8))
    plt.axis('off')
    plt.imshow(make_grid(images, nrow=16).permute((1, 2, 0)))
    break

def get_default_device():
    """Pick GPU if available, else CPU"""
    if torch.cuda.is_available():
        return torch.device('cuda')
    else:
        return torch.device('cpu')
    
def to_device(data, device):
    """Move tensor(s) to chosen device"""
    if isinstance(data, (list,tuple)):
        return [to_device(x, device) for x in data]
    return data.to(device, non_blocking=True)

class DeviceDataLoader():
    """Wrap a dataloader to move data to a device"""
    def __init__(self, dl, device):
        self.dl = dl
        self.device = device
        
    def __iter__(self):
        """Yield a batch of data after moving it to device"""
        for b in self.dl: 
            yield to_device(b, self.device)

    def __len__(self):
        """Number of batches"""
        return len(self.dl)

device = get_default_device()
device

class SimpleResidualBlock(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=3, kernel_size=3, stride=1, padding=1)
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv2d(in_channels=3, out_channels=3, kernel_size=3, stride=1, padding=1)
        self.relu2 = nn.ReLU()
        
    def forward(self, x):
        out = self.conv1(x)
        out = self.relu1(out)
        out = self.conv2(out)
        return self.relu2(out) + x

"""Accuracy calculation """

def accuracy(outputs, labels):
    _, preds = torch.max(outputs, dim=1)
    return torch.tensor(torch.sum(preds == labels).item() / len(preds))

class ImageClassificationBase(nn.Module):
    def training_step(self, batch):
        images, labels = batch 
        out = self(images)                  # Generate predictions
        loss = F.cross_entropy(out, labels) # Calculate loss
        return loss
    
    def validation_step(self, batch):
        images, labels = batch 
        out = self(images)                    # Generate predictions
        loss = F.cross_entropy(out, labels)   # Calculate loss
        acc = accuracy(out, labels)           # Calculate accuracy
        return {'val_loss': loss.detach(), 'val_acc': acc}
        
    def validation_epoch_end(self, outputs):
        batch_losses = [x['val_loss'] for x in outputs]
        epoch_loss = torch.stack(batch_losses).mean()   # Combine losses
        batch_accs = [x['val_acc'] for x in outputs]
        epoch_acc = torch.stack(batch_accs).mean()      # Combine accuracies
        return {'val_loss': epoch_loss.item(), 'val_acc': epoch_acc.item()}
    
    def epoch_end(self, epoch, result):
        print("Epoch [{}], last_lr: {:.5f}, train_loss: {:.4f}, val_loss: {:.4f}, val_acc: {:.4f}".format(
            epoch, result['lrs'][-1], result['train_loss'], result['val_loss'], result['val_acc']))

def conv_block(in_channels, out_channels, pool=False):
    layers = [nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1), 
              nn.BatchNorm2d(out_channels), 
              nn.ReLU(inplace=True)]
    if pool: layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)

class ResNet9(ImageClassificationBase):
    def __init__(self, in_channels, num_classes):
        super().__init__()
        
        self.conv1 = conv_block(in_channels, 64)
        self.conv2 = conv_block(64, 128, pool=True)
        self.res1 = nn.Sequential(conv_block(128, 128), conv_block(128, 128))
        
        self.conv3 = conv_block(128, 256, pool=True)
        self.conv4 = conv_block(256, 512, pool=True)
        self.res2 = nn.Sequential(conv_block(512, 512), conv_block(512, 512))
        
        self.classifier = nn.Sequential(nn.MaxPool2d(4), 
                                        nn.Flatten(), 
                                        nn.Dropout(0.2),
                                        nn.Linear(512, num_classes))
        
    def forward(self, xb):
        out = self.conv1(xb)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        out = self.classifier(out)
        return out

a = torch.randn(4, 4)
a

tb = SummaryWriter()

_,preds=torch.max(a, 1)
preds

model = to_device(ResNet9(3, 10), device)
model

@torch.no_grad()
def evaluate(model, val_loader):
    model.eval()
    outputs = [model.validation_step(batch) for batch in val_loader]
    return model.validation_epoch_end(outputs)

def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']

def fit_one_cycle(epochs, max_lr, model, train_loader, val_loader, 
                  weight_decay=0, grad_clip=None, opt_func=torch.optim.SGD):
    torch.cuda.empty_cache()
    history = []
    
    # Set up cutom optimizer with weight decay
    optimizer = opt_func(model.parameters(), max_lr, weight_decay=weight_decay)
    # Set up one-cycle learning rate scheduler
    sched = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr, epochs=epochs, 
                                                steps_per_epoch=len(train_loader))
    
    for epoch in range(epochs):
        # Training Phase 
        model.train()
        train_losses = []
        total_loss=[]
        lrs = []
        for batch in train_loader:
            total_loss = 0
            total_correct = 0
            loss = model.training_step(batch)
            train_losses.append(loss)
            loss.backward()
            
            # Gradient clipping
            if grad_clip: 
                nn.utils.clip_grad_value_(model.parameters(), grad_clip)
            
            optimizer.step()
            optimizer.zero_grad()
            
            # Record & update learning rate
            lrs.append(get_lr(optimizer))
            sched.step()
            # Pass Batch
            # Calculate Loss
            # Calculate Gradient
            # Update Weights
        for name, param in model.named_parameters():
                tb.add_histogram(name, param, epoch)
                tb.add_histogram(f'{name}.grad', param.grad, epoch) 
        #tb.add_histogram('conv1.bias',model.conv1.bias, epoch)
        #tb.add_histogram('conv1.weight',model.conv1.weight, epoch)
        #tb.add_histogram('conv1.weight.grad',model.conv1.weight.grad,epoch)
 
            
           
        # Validation phase
        tb.add_scalar('Loss', total_loss, epoch)
        tb.add_scalar('Number Correct', total_correct, epoch)
        tb.add_scalar('Accuracy', total_correct / len(train_set), epoch)
        result = evaluate(model, val_loader)
        result['train_loss'] = torch.stack(train_losses).mean().item()
        result['lrs'] = lrs
        model.epoch_end(epoch, result)
        history.append(result)
    return history

train_dl=DeviceDataLoader(train_dl,device)
valid_dl=DeviceDataLoader(valid_dl,device)

history = [evaluate(model, valid_dl)]
history

epochs = 8
max_lr = 0.01
grad_clip = 0.1
weight_decay = 1e-4
opt_func = torch.optim.Adam

# Commented out IPython magic to ensure Python compatibility.
# %%time
# history += fit_one_cycle(epochs, max_lr, model, train_dl, valid_dl, 
#                              grad_clip=grad_clip, 
#                              weight_decay=weight_decay, 
#                              opt_func=opt_func)

# Commented out IPython magic to ensure Python compatibility.
# %reload_ext tensorboard
# %tensorboard --logdir=logs

print("hellow world ")

a=1 
b=2
c= a+b
print(c)

tensorboard --logdir=runs