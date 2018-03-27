import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {axiosInstance} from '../tools.js';
import LinearProgress from 'material-ui/LinearProgress';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import Toggle from 'material-ui/Toggle';
import FlatButton from 'material-ui/FlatButton';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';
import TouchRipple from 'material-ui/internal/TouchRipple';

class ServiceToggle extends Component {
  constructor(props) {
    /*
    title:
    subtitle:
    avatarColor:
    avatarIcon:
    toggled:
    changeStatus(function):
    */
    super(props);
  }

  render() {
    return <table>
            <tr>
              <td width="100%">
                <CardHeader
                    title={this.props.title}
                    subtitle={this.props.subtitle}
                    avatar={
                      <Avatar 
                        backgroundColor={this.props.avatarColor} 
                        icon={<FontIcon className="material-icons">{this.props.avatarIcon}</FontIcon>}
                      />
                    }
                />
              </td>
              <td align="right">
                <Toggle toggled={this.props.toggled !== null ? this.props.toggled : false}
                        disabled={this.props.toggled === null} 
                        onToggle={this.props.changeStatus} 
                        style={{float:"right", margin:"4px"}}/>
              </td>
            </tr>
          </table>;
  }
}

class EngineStatus extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'miner': null,
      'power': null,
      'peers_check': null,
      'peer_receive': null,
      'blockchain': null
    }
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axiosInstance.get("/engine").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['miner'] = data.miner == 'RUNNING';
        state['power'] = data.power == 'RUNNING';
        state['blockchain'] = data.blockchain == 'RUNNING';
        state['peers_check'] = data.peers_check == 'RUNNING';
        state['peer_receive'] = data.peer_receive == 'RUNNING';
        return state;
      });
    });
  }

  changeStatus = (service_name) => {
    if(this.state[service_name]) {
      console.log('Stoppping ' + service_name);
      axiosInstance.post("/service/" + service_name + "/stop").then((response) => {
        this.update();
      });
    }
    else {
      console.log('Starting ' + service_name);
      axiosInstance.post("/service/" + service_name + "/start").then((response) => {
        this.update();
      });
    }
  }

  render() {
    return (
      <Card containerStyle={{height:"100%"}}>
        <ServiceToggle 
          title="Blockchain" subtitle={this.state.blockchain? "Running":"Closed"} avatarIcon="build" 
          avatarColor={this.state.blockchain ? green500:red500} toggled={this.state.blockchain} 
          changeStatus={() => {this.changeStatus('blockchain')}}
        />
        <ServiceToggle 
          title="Peers Check" subtitle={this.state.peers_check? "Running":"Closed"} avatarIcon="build" 
          avatarColor={this.state.peers_check ? green500:red500} toggled={this.state.peers_check} 
          changeStatus={() => {this.changeStatus('peers_check')}}
        />
        <ServiceToggle 
          title="Peer Listen" subtitle={this.state.peer_receive? "Running":"Closed"} avatarIcon="build" 
          avatarColor={this.state.peer_receive ? green500:red500} toggled={this.state.peer_receive} 
          changeStatus={() => {this.changeStatus('peer_receive')}}
        />
        <ServiceToggle 
          title="Miner" subtitle={this.state.miner? "Running":"Closed"} avatarIcon="build" 
          avatarColor={this.state.miner ? green500:red500} toggled={this.state.miner} 
          changeStatus={() => {this.changeStatus('miner')}}
        />
        <ServiceToggle 
          title="Power" subtitle={this.state.power? "Running":"Closed"} avatarIcon="build" 
          avatarColor={this.state.power ? green500:red500} toggled={this.state.power} 
          changeStatus={() => {this.changeStatus('power')}}
        />
      </Card>
    );
  }
}

export default EngineStatus;