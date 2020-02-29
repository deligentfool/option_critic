import torch
import torch.nn as nn
import torch.nn.functional as F
from replay_buffer import replay_buffer
import numpy as np


class opt_cri_arch(nn.Module):
    def __init__(self, observation_dim, action_dim, option_num):
        super(opt_cri_arch, self).__init__()
        self.observation_dim = observation_dim
        self.action_dim = action_dim
        self.option_num = option_num

        self.feature = nn.Sequential(
            nn.Linear(self.observation_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )

        self.q_value_layer = nn.Linear(128, self.option_num)

        self.termination_layer = nn.Linear(128, self.option_num)
        self.option_layer = [nn.Linear(128, self.action_dim) for _ in range(self.option_num)]

    def get_state(self, observation):
        return self.feature(observation)

    def get_q_value(self, state):
        return self.q_value_layer(state)

    def get_option_termination(self, state, current_option):
        termination = self.termination_layer(state)[:, current_option].sigmoid()
        if self.training:
            option_termination = torch.distributions.Bernoulli(termination)
        else:
            option_termination = (termination > 0.5)
        q_value = self.get_q_value(state)
        next_option = q_value.max(1)[1].detach().item()
        return bool(option_termination), next_option

    def get_termination(self, state):
        return self.termination_layer(state).sigmoid()

    def get_action(self, state, current_option):
        x = self.option_layer[current_option](state)
        prob = F.softmax(x, dim=1)
        dist = torch.distributions.Categorical(prob)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        entropy = dist.entropy()
        action = action.detach().item()
        return action, log_prob, entropy

    def get_option(self, state):
        q_value = self.get_q_value(state)
        next_option = q_value.max(1)[1].detach().item()
        return next_option