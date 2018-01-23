import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';

class Balance extends Component {

  render() {
    let balance = 0;
    let name = "";
    if(this.props.wallet !== null){
      balance = this.props.wallet.balance;
      console.log(balance);
      name = this.props.wallet.name;
    }
    return (
      <Card>
        <CardHeader
          title="Balance"
          subtitle={balance}
          avatar={<Avatar backgroundColor={green500} icon={<FontIcon className="material-icons">trending_up</FontIcon>} />}
        />
      </Card>
      
    );
  }
}

export default Balance;