import React, { Component } from 'react';
import {axiosInstance} from '../tools.js';
import {Card, CardHeader, } from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import Toggle from 'material-ui/Toggle';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';
import RaisedButton from 'material-ui/RaisedButton';

class ServiceToggle extends Component {

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
      'blockchain': null,
      'dialogTitle': '',
      'dialogOpen': false,
      'password': ''
    }
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axiosInstance.get("/engine").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['miner'] = data.miner === 'RUNNING';
        state['power'] = data.power === 'RUNNING';
        state['blockchain'] = data.blockchain === 'RUNNING';
        state['peers_check'] = data.peers_check === 'RUNNING';
        state['peer_receive'] = data.peer_receive === 'RUNNING';
        return state;
      });
    });
  }

  handleOpen = (dialog_title) => {
    this.setState({dialogOpen: true, dialogTitle: dialog_title});
  };

  handleClose = () => {
    this.setState({dialogOpen: false, password:'', dialogTitle:''});
  };

  onPasswordChange = (e) => {
    this.setState({password: e.target.value});
  }

  changeStatus = (service_name) => {
    if(this.state[service_name]) {
      axiosInstance.post("/service/" + service_name + "/stop").then((response) => {
        this.update();
      });
    }
    else {
      if(service_name === "power" || service_name === "miner") {
        this.handleOpen(service_name);
      }
      else{
        axiosInstance.post("/service/" + service_name + "/start").then((response) => {
          this.update();
        });
      }
    }
  }

  startWithPassword = () => {
    let data = new FormData();
    data.append('password', this.state.password);
    axiosInstance.post("/service/" + this.state.dialogTitle + "/start", data).then((response) => {
      this.handleClose();
      this.update();
    }).catch((error) => {
      this.handleClose();
    });
  }

  render() {
    const actions = [
      <RaisedButton
        label="Ok"
        primary={true}
        keyboardFocused={true}
        onClick={this.startWithPassword}
      />,
    ];

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
        <Dialog
          title="Enter Password"
          actions={actions}
          modal={false}
          open={this.state.dialogOpen}
          onRequestClose={this.handleClose}
        >
          <TextField
              fullWidth={true}
              floatingLabelText="Password"
              name="password"
              type="password"
              onChange={this.onPasswordChange}
            />
        </Dialog>
      </Card>
    );
  }
}

export default EngineStatus;