""" LSTM models. """

import torch
import torch.nn as nn
import torch.nn.functional as F


class LSTM_tele(nn.Module):
    """
    LSTM model that takes in the gradient of two layers.
    Returns a group element for teleportation.
    """
    def __init__(self, input_dim, lstm_hidden_dim, out_dim, preproc=False):
        super(LSTM_tele, self).__init__()

        self.input_dim = input_dim
        self.out_dim = out_dim
        self.lstm_hidden_dim = lstm_hidden_dim

        self.lstm1 = nn.LSTMCell(input_dim, lstm_hidden_dim)
        self.lstm2 = nn.LSTMCell(lstm_hidden_dim, lstm_hidden_dim)
        self.linear = nn.Linear(lstm_hidden_dim, out_dim*out_dim)


    def forward(self, dL_dU, dL_dV, hidden, cell):
        grad_flatten = torch.cat((torch.flatten(dL_dU), torch.flatten(dL_dV)), 0)
        grad_flatten = grad_flatten[None, :]

        h0, c0 = self.lstm1(grad_flatten, (hidden[0], cell[0]))
        h1, c1 = self.lstm2(h0, (hidden[1], cell[1]))
        g = self.linear(h1)
        g = torch.reshape(g, (self.out_dim, self.out_dim))
        return g, torch.stack((h0, h1)), torch.stack((c0, c1))

class LSTM_tele_lr(nn.Module):
    """
    LSTM model that takes in the gradient of two layers.
    Returns group elements for teleportation.
    """
    def __init__(self, input_dim, lstm_hidden_dim, out_dim):
        super(LSTM_tele_lr, self).__init__()

        self.input_dim = input_dim
        self.out_dim = out_dim
        self.lstm_hidden_dim = lstm_hidden_dim

        # Define LSTM cells and linear layers
        self.lstm1 = nn.LSTMCell(input_dim, lstm_hidden_dim)
        self.lstm2 = nn.LSTMCell(lstm_hidden_dim, lstm_hidden_dim)
        self.linear1 = nn.Linear(lstm_hidden_dim, out_dim*out_dim)  # for teleportation operator
        self.linear2 = nn.Linear(lstm_hidden_dim, 1)  # for step size
        self.linear3 = nn.Linear(lstm_hidden_dim, 1)  # for momentum coefficient (m_c)

    def forward(self, dL_dU, dL_dV, hidden, cell):
        # Concatenate gradients from two layers
        grad_flatten = torch.cat((torch.flatten(dL_dU), torch.flatten(dL_dV)), 0)
        grad_flatten = grad_flatten[None, :]

        # LSTM forward pass
        h0, c0 = self.lstm1(grad_flatten, (hidden[0], cell[0]))
        h1, c1 = self.lstm2(h0, (hidden[1], cell[1]))

        # Calculate outputs
        g = self.linear1(h1)  # teleportation operator
        g = torch.reshape(g, (self.out_dim, self.out_dim))

        step_size = torch.clamp(self.linear2(h1), min=1e-7, max=5e-3)  # step size
        # m_c = torch.clamp(self.linear3(h0), min=0, max=1)  # momentum coefficient
        m_c = torch.clamp(2 * torch.clamp(self.linear3(h0), min=0, max=1), min=0, max=1)

        return g, step_size, m_c, torch.stack((h0, h1)), torch.stack((c0, c1))


class LSTM_local_update(nn.Module):
    """
    LSTM model that takes in the gradient of all weights and returns the local update.
    input_dim and output_dim are expected to be the same.
    """
    def __init__(self, input_dim, lstm_hidden_dim, out_dim, preproc=False):
        super(LSTM_local_update, self).__init__()

        self.input_dim = input_dim
        self.out_dim = out_dim
        self.lstm_hidden_dim = lstm_hidden_dim

        self.lstm1 = nn.LSTMCell(input_dim, lstm_hidden_dim)
        self.lstm2 = nn.LSTMCell(lstm_hidden_dim, lstm_hidden_dim)
        self.linear = nn.Linear(lstm_hidden_dim, out_dim)


    def forward(self, grad_flatten, hidden, cell):
        grad_flatten = grad_flatten[None, :]

        h0, c0 = self.lstm1(grad_flatten, (hidden[0], cell[0]))
        h1, c1 = self.lstm2(h0, (hidden[1], cell[1]))
        update = self.linear(h1)
        update = torch.squeeze(update)
        update = torch.clamp(update, min=-1e7, max=1e7)
        
        return update, torch.stack((h0, h1)), torch.stack((c0, c1))



