import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import axios from 'axios';
import LinearProgress from 'material-ui/LinearProgress';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FlatButton from 'material-ui/FlatButton';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';
import Toggle from 'material-ui/Toggle';

class Power extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'status': 'Loading...',
      'description': '',
      'running': false
    }
    this.props.socket.on('power_status', (data) => {
      this.setState((state) => {
        state['running'] = data.running;
        state['status'] = data.status;
        state['description'] = data.description;
        return state;
      });
    });
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axios.get("/power").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['running'] = data.running;
        state['status'] = data.status;
        state['description'] = data.description;
        return state;
      });
    });
  }

  powerChangeStatus = () => {
    if(this.state.running === null) {
      return;
    }

    if(this.state.running) {
      axios.post("/power/stop").then((response) => {
        this.update();
      });
    }
    else {
      axios.post("/power/start").then((response) => {
        this.update();
      });
    }
  }

  render() {
    return (
      <table>
        <tr>
          <td width="100%">
            <CardHeader
                title="Power"
                subtitle={this.state.running ? "Running":"Closed"}
                avatar={
                  <Avatar 
                    style={{cursor:"pointer"}}
                    backgroundColor={this.state.running ? green500:red500} 
                    icon={<FontIcon className="material-icons">build</FontIcon>} 
                  />
                }
            />
          </td>
          <td align="right">
            <Toggle toggled={this.state.running} 
                    onToggle={this.powerChangeStatus} 
                    style={{float:"right", margin:"4px"}}/>
          </td>
        </tr>
      </table>
    );
  }
}

export default Power;