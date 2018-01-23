import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {axiosInstance} from '../tools.js';
import LinearProgress from 'material-ui/LinearProgress';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FlatButton from 'material-ui/FlatButton';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';
import TouchRipple from 'material-ui/internal/TouchRipple';

class Miner extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'running': null,
      'cpu': 0
    }
    this.minerChangeStatus = this.minerChangeStatus.bind(this);
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axiosInstance.get("/status_miner").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['running'] = data.running;
        if(data.running)
          state['cpu'] = data.cpu;
        return state;
      });
    });
  }

  minerChangeStatus() {
    if(this.state.running === null) {
      return;
    }

    if(this.state.running) {
      axiosInstance.get("/stop_miner").then((response) => {
        this.update();
      });
    }
    else {
      axiosInstance.get("/start_miner").then((response) => {
        this.update();
      });
    }
  }

  render() {
    let content = 'Loading';
    let color = 'yellow';
    let button_text = 'Loading';
    let button_type = "info";
    let progressBar = <div />;
    if(this.state.running === false) {
      content = "Closed";
      color = red500;
      button_text = "Start";
      button_type = "success";
    }
    else if(this.state.running) {
      content = "Running";
      color = green500;
      button_text = "Stop";
      button_type = "danger";
      progressBar = <LinearProgress style={{padding:32}} mode="determinate" value={this.state.cpu} max={100} />;
    }
    return (
      <Card containerStyle={{height:"100%"}}>
        <CardHeader
          title="Miner"
          subtitle={content}
          avatar={
            <Avatar 
              style={{cursor:"pointer"}}
              onClick={()=>{this.props.notify('Miner module tries to generate new blocks.')}} 
              backgroundColor={color} 
              icon={<FontIcon className="material-icons">build</FontIcon>} 
            />
          }
        />
        <CardActions style={{ width: '100%', textAlign: 'right' }}>
          <FlatButton label={button_text} onClick={this.minerChangeStatus} />
        </CardActions>
      </Card>
    );
  }
}

export default Miner;
/*

        <div className="card card-stats">
          <div className="card-header" data-background-color={color}>
            <i className="material-icons">build</i>
          </div>
          <div className="card-content">
            <p className="category">Miner Status</p>
            <h3 className="title">{content}</h3>
            {progressBar}
          </div>
          <div className="card-footer">
            <div className="stats" style={{"float":"right"}}>
              <button className={'btn btn-' + button_type} onClick={this.minerChangeStatus}>{button_text}</button>
            </div>
          </div>
        </div>
*/