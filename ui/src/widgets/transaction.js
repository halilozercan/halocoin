import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';

class Transaction extends Component {

  render() {
    let details = "";
    if(this.props.tx.type == 'reward') {
        details = "Rewardee: " + this.props.tx.to + " JobId: " + this.props.tx.job_id;
    }
    else if(this.props.tx.type == 'spend') {
        details = "Recipient: " + this.props.tx.to + " Amount: " + this.props.tx.amount;
    }

    return (
      <Card>
        <CardHeader
          title={this.props.tx.type}
          subtitle={this.props.tx.issuer}
        />
        <CardText>
            {details}
        </CardText>
      </Card>
      
    );
  }
}

export default Transaction;