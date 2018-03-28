import React, { Component } from 'react';
//import {shell} from 'electron';
import {MCardStats} from '../components/card.js';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import RaisedButton from 'material-ui/RaisedButton';

class Authority extends Component {

  constructor(props) {
    /**
     * name
     * supply
     * avatar
     * description
     * rewardDistributed
     * rewardPool
     * webAddress
     */
    super(props);
  }

  render() {

    return (
      <Card>
        <CardHeader
          title={this.props.name}
          titleStyle={{fontSize:"18px"}}
          subtitle={"Work Description: " + this.props.description}
          //avatar={this.props.avatar}
        />
        <CardText>
            <p>Remaining Supply: <b>{this.props.supply}</b></p>
            <p>Total Reward Distributed: <b>{this.props.rewardDistributed}</b></p>
            <p>Total Reward in the Pool: <b>{this.props.rewardPool}</b></p>
        </CardText>
        <CardActions align='right'>
          <RaisedButton label="Homepage" primary={true} onClick={() => {
              const shell = window.require('electron').shell;
              let result = shell.openExternal(this.props.webAddress);
              console.log('Click result: ' + result);
            }} />
        </CardActions>
      </Card>
      
    );
  }
}

export default Authority;