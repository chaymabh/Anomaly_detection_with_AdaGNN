import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.parameter import Parameter
from torch.nn.modules.module import Module
import matplotlib.pyplot as plt

class Adagnn_without_weight(Module):

    def __init__(self, diag_dimension, in_features, out_features, bias=True):
        super(Adagnn_without_weight, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.diag_dimension = diag_dimension
        self.learnable_diag_1 = Parameter(torch.FloatTensor(in_features))  # in_features

        if bias:
            self.bias = Parameter(torch.FloatTensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()

    def reset_parameters(self):
        torch.nn.init.normal_(self.learnable_diag_1, mean=0, std=0)

    def forward(self, input, l_sym):

        e1 = torch.spmm(l_sym, input)
        alpha = torch.diag(self.learnable_diag_1)
        e2 = torch.mm(e1, alpha)
        e4 = torch.sub(input, e2)
        output = e4

        if self.bias is not None:
            return output + self.bias
        else:
            return output

    def __repr__(self):
        return self.__class__.__name__ + ' (' \
               + str(self.in_features) + ' -> ' \
               + str(self.out_features) + ')'


class Adagnn_with_weight(Module):

    def __init__(self, diag_dimension, in_features, out_features, bias=True):
        super(Adagnn_with_weight, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.diag_dimension = diag_dimension
        self.weight = Parameter(torch.FloatTensor(in_features, out_features))
        self.learnable_diag_1 = Parameter(torch.FloatTensor(in_features))
        if bias:
            self.bias = Parameter(torch.FloatTensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()

    def reset_parameters(self):
        stdv = 1. / math.sqrt(self.weight.size(1))
        self.weight.data.uniform_(-stdv, stdv)
        torch.nn.init.normal_(self.learnable_diag_1, mean=0, std=0.01)
        if self.bias is not None:
            self.bias.data.uniform_(-stdv, stdv)

    def forward(self, input, l_sym):
        e1 = torch.spmm(l_sym, input)
        alpha = torch.diag(self.learnable_diag_1)
        e2 = torch.mm(e1, alpha + torch.eye(self.in_features, self.in_features).cpu())
        e4 = torch.sub(input, e2)
        e5 = torch.mm(e4, self.weight)
        output = e5

        if self.bias is not None:
            return output + self.bias
        else:
            return output

    def __repr__(self):
        return self.__class__.__name__ + ' (' \
               + str(self.in_features) + ' -> ' \
               + str(self.out_features) + ')'

class AdaGNN(nn.Module):
    def __init__(self, diag_dimension, nfeat, nhid, nlayer, nclass, dropout):
        super(AdaGNN, self).__init__()

        self.should_train_1 = Adagnn_with_weight(diag_dimension, nfeat, nhid)
        assert nlayer - 2 >= 0
        self.hidden_layers = nn.ModuleList([
            Adagnn_without_weight(nfeat, nhid, nhid, bias=False)
            for i in range(nlayer - 2)
        ])
        self.should_train_2 = Adagnn_with_weight(diag_dimension, nhid, nclass)
        self.dropout = dropout

    def forward(self, x, l_sym):

        x = F.relu(self.should_train_1(x, l_sym))
        x = F.dropout(x, self.dropout, training=self.training)

        for i, layer in enumerate(self.hidden_layers):
            x = layer(x, l_sym)
            x = F.relu(x)  # Add ReLU activation
            x = F.dropout(x, self.dropout, training=self.training)

        x = self.should_train_2(x, l_sym)
        x = F.relu(x)  # Add ReLU activation

        return F.log_softmax(x, dim=1)

class AdaGNN(nn.Module):
    def __init__(self, diag_dimension, nfeat, nhid, nlayer, nclass, dropout):
        super(AdaGNN, self).__init__()

        self.should_train_1 = Adagnn_with_weight(diag_dimension, nfeat, nhid)
        assert nlayer - 2 >= 0
        self.hidden_layers = nn.ModuleList([
            Adagnn_without_weight(nfeat, nhid, nhid, bias=False)
            for i in range(nlayer - 2)
        ])
        self.should_train_2 = Adagnn_with_weight(diag_dimension, nhid, nclass)
        self.dropout = dropout

    def forward(self, x, l_sym):

        x_before = x.clone()  # Save x before modifying it

        x = F.relu(self.should_train_1(x, l_sym))
        x = F.dropout(x, self.dropout, training=self.training)

        for i, layer in enumerate(self.hidden_layers):
            x = layer(x, l_sym)
            x = F.relu(x)  # Add ReLU activation
            x = F.dropout(x, self.dropout, training=self.training)

        x = self.should_train_2(x, l_sym)
        x = F.relu(x) # Add ReLU activation

        return F.log_softmax(x, dim=1)
